"""
Shopping Cart model
"""
from datetime import datetime, timedelta
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, Field, validator
from pymongo import IndexModel


class CartItem(BaseModel):
    """Shopping cart item model"""

    product_id: str = Field(..., description="Product ID")
    variant_id: str = Field(..., description="Variant ID")
    quantity: int = Field(..., gt=0, description="Quantity in cart")
    price: float = Field(
        ..., gt=0, description="Price at time of adding to cart"
    )
    added_at: datetime = Field(
        default_factory=datetime.utcnow, description="When item was added"
    )


class CartTotals(BaseModel):
    """Cart totals calculation"""

    items_count: int = Field(
        default=0, ge=0, description="Total number of items"
    )
    subtotal: float = Field(
        default=0.0, ge=0, description="Subtotal of all items"
    )
    estimated_tax: float = Field(
        default=0.0, ge=0, description="Estimated tax"
    )
    estimated_shipping: float = Field(
        default=0.0, ge=0, description="Estimated shipping"
    )
    estimated_total: float = Field(
        default=0.0, ge=0, description="Estimated total"
    )


class Cart(Document):
    """Shopping cart document model"""

    user_id: Optional[str] = Field(
        None, description="User ID (null for anonymous carts)"
    )
    session_id: Optional[str] = Field(
        None, description="Session ID for anonymous users"
    )
    items: List[CartItem] = Field(
        default_factory=list, description="Cart items"
    )
    totals: CartTotals = Field(
        default_factory=CartTotals, description="Cart totals"
    )
    expires_at: datetime = Field(..., description="Cart expiration date")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "carts"
        indexes = [
            IndexModel([("user_id", 1)]),
            IndexModel([("session_id", 1)]),
            IndexModel([("expires_at", 1)], expireAfterSeconds=0),
        ]

    @validator("expires_at", pre=True, always=True)
    def set_expiry(cls, v):
        if not v:
            return datetime.utcnow() + timedelta(
                days=7
            )  # Cart expires in 7 days
        return v

    def add_item(
        self, product_id: str, variant_id: str, quantity: int, price: float
    ):
        """Add item to cart or update quantity if it already exists"""
        for item in self.items:
            if item.product_id == product_id and item.variant_id == variant_id:
                item.quantity += quantity
                item.added_at = datetime.utcnow()
                self.updated_at = datetime.utcnow()
                self.calculate_totals()
                return

        # Item not found, add new item
        new_item = CartItem(
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            price=price,
        )
        self.items.append(new_item)
        self.updated_at = datetime.utcnow()
        self.calculate_totals()

    def update_item_quantity(
        self, product_id: str, variant_id: str, quantity: int
    ):
        """Update quantity of specific item"""
        for i, item in enumerate(self.items):
            if item.product_id == product_id and item.variant_id == variant_id:
                if quantity <= 0:
                    self.items.pop(i)
                else:
                    item.quantity = quantity
                    item.added_at = datetime.utcnow()
                self.updated_at = datetime.utcnow()
                self.calculate_totals()
                return True
        return False

    def remove_item(self, product_id: str, variant_id: str):
        """Remove item from cart"""
        for i, item in enumerate(self.items):
            if item.product_id == product_id and item.variant_id == variant_id:
                self.items.pop(i)
                self.updated_at = datetime.utcnow()
                self.calculate_totals()
                return True
        return False

    def clear_cart(self):
        """Clear all items from cart"""
        self.items = []
        self.updated_at = datetime.utcnow()
        self.calculate_totals()

    def calculate_totals(self):
        """Calculate cart totals"""
        self.totals.items_count = sum(item.quantity for item in self.items)
        self.totals.subtotal = sum(
            item.price * item.quantity for item in self.items
        )

        # Calculate estimated tax (assuming 8% tax rate)
        self.totals.estimated_tax = self.totals.subtotal * 0.08

        # Calculate estimated shipping (free shipping over $50)
        if self.totals.subtotal >= 50:
            self.totals.estimated_shipping = 0.0
        else:
            self.totals.estimated_shipping = 9.99

        self.totals.estimated_total = (
            self.totals.subtotal
            + self.totals.estimated_tax
            + self.totals.estimated_shipping
        )

    def is_empty(self) -> bool:
        """Check if cart is empty"""
        return len(self.items) == 0

    def get_item_count(self) -> int:
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items)


# Request/Response Models


class CartItemAdd(BaseModel):
    """Schema for adding item to cart"""

    product_id: str = Field(..., description="Product ID")
    variant_id: str = Field(..., description="Variant ID")
    quantity: int = Field(..., gt=0, description="Quantity to add")


class CartItemUpdate(BaseModel):
    """Schema for updating cart item"""

    product_id: str = Field(..., description="Product ID")
    variant_id: str = Field(..., description="Variant ID")
    quantity: int = Field(..., ge=0, description="New quantity (0 to remove)")


class CartItemRemove(BaseModel):
    """Schema for removing cart item"""

    product_id: str = Field(..., description="Product ID")
    variant_id: str = Field(..., description="Variant ID")


class CartItemResponse(BaseModel):
    """Schema for cart item response"""

    product_id: str = Field(..., description="Product ID")
    variant_id: str = Field(..., description="Variant ID")
    quantity: int = Field(..., description="Quantity in cart")
    price: float = Field(..., description="Unit price")
    total: float = Field(..., description="Total price for this item")
    added_at: datetime = Field(..., description="When item was added")
    # These fields would be populated from product lookup
    product_name: Optional[str] = Field(None, description="Product name")
    variant_name: Optional[str] = Field(None, description="Variant name")
    product_image: Optional[str] = Field(None, description="Product image URL")
    sku: Optional[str] = Field(None, description="Product SKU")


class CartResponse(BaseModel):
    """Schema for cart response"""

    id: str = Field(..., description="Cart ID")
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    items: List[CartItemResponse] = Field(..., description="Cart items")
    totals: CartTotals = Field(..., description="Cart totals")
    expires_at: datetime = Field(..., description="Cart expiration")
    created_at: datetime = Field(..., description="Creation date")
    updated_at: datetime = Field(..., description="Last update date")


class CartMerge(BaseModel):
    """Schema for merging anonymous cart with user cart"""

    session_id: str = Field(..., description="Anonymous session ID")
