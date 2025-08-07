"""
Order endpoints
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user_id
from app.models.cart import Cart
from app.models.order import (
    Order,
    OrderCreate,
    OrderItem,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdate,
    OrderSummary,
    PaymentInfo,
)
from app.models.product import Product
from app.models.user import User

router = APIRouter()


async def calculate_order_totals(items: List[OrderItem]) -> OrderSummary:
    """Calculate order totals"""
    subtotal = sum(item.total for item in items)

    # Calculate tax (8% rate)
    tax = round(subtotal * 0.08, 2)

    # Calculate shipping (free over $50)
    shipping = 0.0 if subtotal >= 50 else 9.99

    # No discount for now
    discount = 0.0

    total = subtotal + tax + shipping - discount

    return OrderSummary(
        subtotal=subtotal,
        tax=tax,
        shipping=shipping,
        discount=discount,
        total=round(total, 2),
    )


@router.post(
    "/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED
)
async def create_order(
    order_data: OrderCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Any:
    """
    Create a new order

    Args:
        order_data: Order creation data
        current_user_id: Current user ID

    Returns:
        Created order

    Raises:
        HTTPException: If validation fails or insufficient stock
    """
    # Get user
    user = await User.get(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Get shipping address
    shipping_address = None
    for addr in user.addresses:
        if addr.address_id == order_data.shipping_address_id:
            shipping_address = addr
            break

    if not shipping_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipping address not found",
        )

    # Get billing address (use shipping if not specified)
    billing_address = shipping_address
    if order_data.billing_address_id:
        for addr in user.addresses:
            if addr.address_id == order_data.billing_address_id:
                billing_address = addr
                break

    # Get payment method
    payment_method = None
    for pm in user.payment_methods:
        if pm.method_id == order_data.payment_method_id:
            payment_method = pm
            break

    if not payment_method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )

    # Process order items
    order_items = []
    total_amount = 0.0

    for item_data in order_data.items:
        # Get product and variant
        product = await Product.get(item_data.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item_data.product_id} not found",
            )

        variant = product.get_variant_by_id(item_data.variant_id)
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product variant {item_data.variant_id} not found",
            )

        # Check stock availability
        if variant.inventory.quantity < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient stock for {product.name}. "
                    f"Available: {variant.inventory.quantity}"
                ),
            )

        # Create order item
        item_total = variant.price * item_data.quantity
        order_item = OrderItem(
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            sku=variant.sku,
            name=f"{product.name} - {variant.name}",
            price=variant.price,
            quantity=item_data.quantity,
            total=item_total,
        )
        order_items.append(order_item)
        total_amount += item_total

    # Calculate order totals
    order_summary = await calculate_order_totals(order_items)

    # Create payment info (would integrate with Stripe in production)
    payment_info = PaymentInfo(
        method=payment_method.type,
        status="pending",
        transaction_id=f"txn_{uuid.uuid4().hex[:16]}",
        amount=order_summary.total,
        currency="USD",
    )

    # Generate order number
    order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    # Create order
    order = Order(
        order_number=order_number,
        user_id=current_user_id,
        items=order_items,
        summary=order_summary,
        shipping_address=shipping_address,
        billing_address=billing_address,
        payment=payment_info,
        notes=order_data.notes,
    )

    # Add initial timeline entry
    order.add_timeline_entry("pending", "Order placed")

    await order.save()

    # Update inventory (reserve stock)
    for item_data in order_data.items:
        product = await Product.get(item_data.product_id)
        if product:
            for variant in product.variants:
                if variant.variant_id == item_data.variant_id:
                    variant.inventory.quantity -= item_data.quantity
                    variant.inventory.reserved += item_data.quantity
                    break
            await product.save()

    # Clear user's cart after successful order
    user_cart = await Cart.find_one(Cart.user_id == current_user_id)
    if user_cart:
        user_cart.clear_cart()
        await user_cart.save()

    # Add loyalty points (1 point per dollar spent)
    points_earned = int(order_summary.total)
    user.add_loyalty_points(points_earned, order_summary.total)
    await user.save()

    return OrderResponse(
        id=str(order.id),
        order_number=order.order_number,
        user_id=order.user_id,
        status=order.status,
        items=order.items,
        summary=order.summary,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        payment=order.payment,
        shipping=order.shipping,
        timeline=order.timeline,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.get("/", response_model=OrderListResponse)
async def get_user_orders(
    current_user_id: str = Depends(get_current_user_id),
    status: Optional[str] = Query(None, description="Filter by order status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> Any:
    """
    Get user's orders

    Args:
        current_user_id: Current user ID
        status: Filter by order status
        page: Page number
        limit: Items per page

    Returns:
        Paginated list of user orders
    """
    # Build query
    query = Order.user_id == current_user_id
    if status:
        query = Order.user_id == current_user_id and Order.status == status

    # Get total count
    total = await Order.find(query).count()

    # Get orders with pagination
    skip = (page - 1) * limit
    orders = (
        await Order.find(query)
        .sort(-Order.created_at)
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    # Convert to response format
    order_responses = []
    for order in orders:
        order_response = OrderResponse(
            id=str(order.id),
            order_number=order.order_number,
            user_id=order.user_id,
            status=order.status,
            items=order.items,
            summary=order.summary,
            shipping_address=order.shipping_address,
            billing_address=order.billing_address,
            payment=order.payment,
            shipping=order.shipping,
            timeline=order.timeline,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        order_responses.append(order_response)

    total_pages = (total + limit - 1) // limit

    return OrderListResponse(
        orders=order_responses,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str, current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Get order by ID

    Args:
        order_id: Order ID
        current_user_id: Current user ID

    Returns:
        Order details

    Raises:
        HTTPException: If order not found or not owned by user
    """
    order = await Order.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # Check if order belongs to current user
    if order.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    return OrderResponse(
        id=str(order.id),
        order_number=order.order_number,
        user_id=order.user_id,
        status=order.status,
        items=order.items,
        summary=order.summary,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        payment=order.payment,
        shipping=order.shipping,
        timeline=order.timeline,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> Any:
    """
    Update order status (for admin users or order owners with limited statuses)

    Args:
        order_id: Order ID
        status_update: Status update data
        current_user_id: Current user ID

    Returns:
        Updated order

    Raises:
        HTTPException: If order not found or unauthorized
    """
    order = await Order.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # Check permissions (users can only cancel their own orders)
    if order.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    # Users can only cancel pending orders
    if status_update.status == "cancelled" and order.status == "pending":
        order.add_timeline_entry(status_update.status, status_update.note)

        # Restore inventory
        for item in order.items:
            product = await Product.get(item.product_id)
            if product:
                for variant in product.variants:
                    if variant.variant_id == item.variant_id:
                        variant.inventory.quantity += item.quantity
                        variant.inventory.reserved -= item.quantity
                        break
                await product.save()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status update",
        )

    await order.save()

    return OrderResponse(
        id=str(order.id),
        order_number=order.order_number,
        user_id=order.user_id,
        status=order.status,
        items=order.items,
        summary=order.summary,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        payment=order.payment,
        shipping=order.shipping,
        timeline=order.timeline,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.get("/number/{order_number}", response_model=OrderResponse)
async def get_order_by_number(
    order_number: str, current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Get order by order number

    Args:
        order_number: Order number
        current_user_id: Current user ID

    Returns:
        Order details

    Raises:
        HTTPException: If order not found or not owned by user
    """
    order = await Order.find_one(Order.order_number == order_number)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # Check if order belongs to current user
    if order.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    return OrderResponse(
        id=str(order.id),
        order_number=order.order_number,
        user_id=order.user_id,
        status=order.status,
        items=order.items,
        summary=order.summary,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        payment=order.payment,
        shipping=order.shipping,
        timeline=order.timeline,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
