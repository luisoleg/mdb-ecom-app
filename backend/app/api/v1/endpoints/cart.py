"""
Shopping Cart endpoints
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from beanie import PydanticObjectId

from app.core.security import get_current_user_id
from app.models.cart import (
    Cart,
    CartItemAdd,
    CartItemUpdate,
    CartItemRemove,
    CartResponse,
    CartItemResponse,
    CartMerge
)
from app.models.product import Product
from app.models.user import User

router = APIRouter()


async def get_cart_by_user_or_session(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Optional[Cart]:
    """Get cart by user ID or session ID"""
    if user_id:
        return await Cart.find_one(Cart.user_id == user_id)
    elif session_id:
        return await Cart.find_one(Cart.session_id == session_id)
    return None


async def create_cart_for_user_or_session(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Cart:
    """Create new cart for user or session"""
    cart = Cart(
        user_id=user_id,
        session_id=session_id
    )
    await cart.save()
    return cart


async def populate_cart_items(cart: Cart) -> CartResponse:
    """Populate cart items with product information"""
    cart_items = []
    
    for item in cart.items:
        # Get product information
        product = await Product.get(item.product_id)
        if not product:
            continue
        
        variant = product.get_variant_by_id(item.variant_id)
        if not variant:
            continue
        
        cart_item = CartItemResponse(
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            price=item.price,
            total=item.price * item.quantity,
            added_at=item.added_at,
            product_name=product.name,
            variant_name=variant.name,
            product_image=variant.images[0].url if variant.images else None,
            sku=variant.sku
        )
        cart_items.append(cart_item)
    
    return CartResponse(
        id=str(cart.id),
        user_id=cart.user_id,
        session_id=cart.session_id,
        items=cart_items,
        totals=cart.totals,
        expires_at=cart.expires_at,
        created_at=cart.created_at,
        updated_at=cart.updated_at
    )


@router.get("/", response_model=CartResponse)
async def get_cart(
    user_id: Optional[str] = Depends(get_current_user_id),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Any:
    """
    Get user's cart or anonymous cart by session ID
    
    Args:
        user_id: Current user ID (optional for anonymous users)
        x_session_id: Session ID for anonymous users
    
    Returns:
        User's cart with populated product information
    """
    # Get cart
    cart = await get_cart_by_user_or_session(user_id, x_session_id)
    
    if not cart:
        # Create new cart if none exists
        cart = await create_cart_for_user_or_session(user_id, x_session_id)
    
    return await populate_cart_items(cart)


@router.post("/items", response_model=CartResponse)
async def add_item_to_cart(
    item_data: CartItemAdd,
    user_id: Optional[str] = Depends(get_current_user_id),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Any:
    """
    Add item to cart
    
    Args:
        item_data: Item to add to cart
        user_id: Current user ID (optional)
        x_session_id: Session ID for anonymous users
    
    Returns:
        Updated cart
    
    Raises:
        HTTPException: If product or variant not found, or insufficient stock
    """
    # Verify product and variant exist
    product = await Product.get(item_data.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    variant = product.get_variant_by_id(item_data.variant_id)
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found"
        )
    
    # Check stock availability
    if variant.inventory.quantity < item_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {variant.inventory.quantity}"
        )
    
    # Get or create cart
    cart = await get_cart_by_user_or_session(user_id, x_session_id)
    if not cart:
        cart = await create_cart_for_user_or_session(user_id, x_session_id)
    
    # Add item to cart
    cart.add_item(
        product_id=item_data.product_id,
        variant_id=item_data.variant_id,
        quantity=item_data.quantity,
        price=variant.price
    )
    
    await cart.save()
    
    return await populate_cart_items(cart)


@router.patch("/items", response_model=CartResponse)
async def update_cart_item(
    item_data: CartItemUpdate,
    user_id: Optional[str] = Depends(get_current_user_id),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Any:
    """
    Update cart item quantity
    
    Args:
        item_data: Item update data
        user_id: Current user ID (optional)
        x_session_id: Session ID for anonymous users
    
    Returns:
        Updated cart
    
    Raises:
        HTTPException: If cart or item not found, or insufficient stock
    """
    cart = await get_cart_by_user_or_session(user_id, x_session_id)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # If quantity > 0, verify stock availability
    if item_data.quantity > 0:
        product = await Product.get(item_data.product_id)
        if product:
            variant = product.get_variant_by_id(item_data.variant_id)
            if variant and variant.inventory.quantity < item_data.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock. Available: {variant.inventory.quantity}"
                )
    
    # Update item quantity
    success = cart.update_item_quantity(
        product_id=item_data.product_id,
        variant_id=item_data.variant_id,
        quantity=item_data.quantity
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in cart"
        )
    
    await cart.save()
    
    return await populate_cart_items(cart)


@router.delete("/items", response_model=CartResponse)
async def remove_cart_item(
    item_data: CartItemRemove,
    user_id: Optional[str] = Depends(get_current_user_id),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Any:
    """
    Remove item from cart
    
    Args:
        item_data: Item to remove
        user_id: Current user ID (optional)
        x_session_id: Session ID for anonymous users
    
    Returns:
        Updated cart
    
    Raises:
        HTTPException: If cart or item not found
    """
    cart = await get_cart_by_user_or_session(user_id, x_session_id)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    success = cart.remove_item(
        product_id=item_data.product_id,
        variant_id=item_data.variant_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in cart"
        )
    
    await cart.save()
    
    return await populate_cart_items(cart)


@router.delete("/", response_model=CartResponse)
async def clear_cart(
    user_id: Optional[str] = Depends(get_current_user_id),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Any:
    """
    Clear all items from cart
    
    Args:
        user_id: Current user ID (optional)
        x_session_id: Session ID for anonymous users
    
    Returns:
        Empty cart
    
    Raises:
        HTTPException: If cart not found
    """
    cart = await get_cart_by_user_or_session(user_id, x_session_id)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    cart.clear_cart()
    await cart.save()
    
    return await populate_cart_items(cart)


@router.post("/merge", response_model=CartResponse)
async def merge_carts(
    merge_data: CartMerge,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Merge anonymous cart with user cart after login
    
    Args:
        merge_data: Anonymous cart session ID
        current_user_id: Current user ID
    
    Returns:
        Merged cart
    """
    # Get user cart and anonymous cart
    user_cart = await Cart.find_one(Cart.user_id == current_user_id)
    anonymous_cart = await Cart.find_one(Cart.session_id == merge_data.session_id)
    
    if not anonymous_cart or anonymous_cart.is_empty():
        # No anonymous cart to merge, return user cart or create new one
        if not user_cart:
            user_cart = await create_cart_for_user_or_session(user_id=current_user_id)
        return await populate_cart_items(user_cart)
    
    if not user_cart:
        # No user cart exists, convert anonymous cart to user cart
        anonymous_cart.user_id = current_user_id
        anonymous_cart.session_id = None
        await anonymous_cart.save()
        return await populate_cart_items(anonymous_cart)
    
    # Merge items from anonymous cart to user cart
    for item in anonymous_cart.items:
        # Verify product still exists and has stock
        product = await Product.get(item.product_id)
        if not product:
            continue
        
        variant = product.get_variant_by_id(item.variant_id)
        if not variant:
            continue
        
        # Add item to user cart
        user_cart.add_item(
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            price=item.price
        )
    
    # Save merged cart and delete anonymous cart
    await user_cart.save()
    await anonymous_cart.delete()
    
    return await populate_cart_items(user_cart)


@router.get("/count")
async def get_cart_count(
    user_id: Optional[str] = Depends(get_current_user_id),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Any:
    """
    Get cart items count
    
    Args:
        user_id: Current user ID (optional)
        x_session_id: Session ID for anonymous users
    
    Returns:
        Cart items count
    """
    cart = await get_cart_by_user_or_session(user_id, x_session_id)
    
    if not cart:
        return {"count": 0}
    
    return {"count": cart.get_item_count()}