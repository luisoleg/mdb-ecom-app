"""
Order and Cart models
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from beanie import Document, Indexed
from pymongo import IndexModel
from app.models.user import Location, Address


class OrderItem(BaseModel):
    """Order item model"""
    product_id: str = Field(..., description="Product ID")
    variant_id: str = Field(..., description="Variant ID")
    sku: str = Field(..., description="Product SKU")
    name: str = Field(..., description="Product name at time of order")
    price: float = Field(..., gt=0, description="Price at time of order")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    total: float = Field(..., gt=0, description="Total for this item")


class OrderSummary(BaseModel):
    """Order financial summary"""
    subtotal: float = Field(..., ge=0, description="Subtotal before taxes and shipping")
    tax: float = Field(default=0.0, ge=0, description="Tax amount")
    shipping: float = Field(default=0.0, ge=0, description="Shipping cost")
    discount: float = Field(default=0.0, ge=0, description="Discount amount")
    total: float = Field(..., gt=0, description="Final total")


class PaymentInfo(BaseModel):
    """Payment information"""
    method: str = Field(..., description="Payment method: credit_card, debit_card, paypal")
    status: str = Field(..., description="Payment status: pending, completed, failed, refunded")
    transaction_id: str = Field(..., description="Payment processor transaction ID")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="USD", description="Payment currency")
    processed_at: Optional[datetime] = Field(None, description="Payment processing timestamp")


class ShippingInfo(BaseModel):
    """Shipping information"""
    method: str = Field(..., description="Shipping method: standard, express, overnight")
    carrier: Optional[str] = Field(None, description="Shipping carrier")
    tracking_number: Optional[str] = Field(None, description="Tracking number")
    estimated_delivery: Optional[datetime] = Field(None, description="Estimated delivery date")
    actual_delivery: Optional[datetime] = Field(None, description="Actual delivery date")


class OrderTimeline(BaseModel):
    """Order status timeline entry"""
    status: str = Field(..., description="Order status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    note: Optional[str] = Field(None, description="Status change note")


class Order(Document):
    """Order document model"""
    order_number: Indexed(str, unique=True) = Field(..., description="Unique order number")
    user_id: str = Field(..., description="Customer user ID")
    status: str = Field(default="pending", description="Order status")
    items: List[OrderItem] = Field(..., min_items=1, description="Order items")
    summary: OrderSummary = Field(..., description="Order financial summary")
    shipping_address: Address = Field(..., description="Shipping address")
    billing_address: Address = Field(..., description="Billing address")
    payment: PaymentInfo = Field(..., description="Payment information")
    shipping: Optional[ShippingInfo] = Field(None, description="Shipping information")
    timeline: List[OrderTimeline] = Field(default_factory=list, description="Order status timeline")
    notes: Optional[str] = Field(None, description="Order notes")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "orders"
        indexes = [
            IndexModel([("order_number", 1)], unique=True),
            IndexModel([("user_id", 1), ("created_at", -1)]),
            IndexModel([("status", 1), ("created_at", -1)]),
        ]

    def add_timeline_entry(self, status: str, note: Optional[str] = None):
        """Add entry to order timeline"""
        entry = OrderTimeline(status=status, note=note)
        self.timeline.append(entry)
        self.status = status
        self.updated_at = datetime.utcnow()

    def calculate_totals(self):
        """Calculate order totals"""
        self.summary.subtotal = sum(item.total for item in self.items)
        self.summary.total = (
            self.summary.subtotal + 
            self.summary.tax + 
            self.summary.shipping - 
            self.summary.discount
        )

    @validator('order_number', pre=True, always=True)
    def generate_order_number(cls, v):
        if not v:
            import uuid
            timestamp = datetime.utcnow().strftime("%Y%m%d")
            unique_id = str(uuid.uuid4())[:8].upper()
            return f"ORD-{timestamp}-{unique_id}"
        return v


# Request/Response Models

class OrderItemCreate(BaseModel):
    """Schema for creating order items"""
    product_id: str = Field(..., description="Product ID")
    variant_id: str = Field(..., description="Variant ID")
    quantity: int = Field(..., gt=0, description="Quantity to order")


class OrderCreate(BaseModel):
    """Schema for creating orders"""
    items: List[OrderItemCreate] = Field(..., min_items=1, description="Order items")
    shipping_address_id: str = Field(..., description="Shipping address ID")
    billing_address_id: Optional[str] = Field(None, description="Billing address ID")
    payment_method_id: str = Field(..., description="Payment method ID")
    shipping_method: str = Field(default="standard", description="Shipping method")
    notes: Optional[str] = Field(None, description="Order notes")


class OrderResponse(BaseModel):
    """Schema for order response"""
    id: str = Field(..., description="Order ID")
    order_number: str = Field(..., description="Order number")
    user_id: str = Field(..., description="Customer user ID")
    status: str = Field(..., description="Order status")
    items: List[OrderItem] = Field(..., description="Order items")
    summary: OrderSummary = Field(..., description="Order summary")
    shipping_address: Address = Field(..., description="Shipping address")
    billing_address: Address = Field(..., description="Billing address")
    payment: PaymentInfo = Field(..., description="Payment information")
    shipping: Optional[ShippingInfo] = Field(None, description="Shipping information")
    timeline: List[OrderTimeline] = Field(..., description="Order timeline")
    notes: Optional[str] = Field(None, description="Order notes")
    created_at: datetime = Field(..., description="Order creation date")
    updated_at: datetime = Field(..., description="Last update date")


class OrderListResponse(BaseModel):
    """Schema for order list response"""
    orders: List[OrderResponse] = Field(..., description="List of orders")
    total: int = Field(..., description="Total number of orders")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status"""
    status: str = Field(..., description="New order status")
    note: Optional[str] = Field(None, description="Status change note")
    tracking_number: Optional[str] = Field(None, description="Tracking number")
    carrier: Optional[str] = Field(None, description="Shipping carrier")