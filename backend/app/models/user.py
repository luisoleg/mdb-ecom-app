"""
User model and related schemas
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
from beanie import Document, Indexed
from pymongo import IndexModel, GEO2D


class Location(BaseModel):
    """Geographic location using GeoJSON Point format"""
    type: str = Field(default="Point")
    coordinates: List[float] = Field(..., description="[longitude, latitude]")


class Address(BaseModel):
    """User address model"""
    address_id: str = Field(..., description="Unique address identifier")
    type: str = Field(..., description="Address type: shipping, billing")
    is_default: bool = Field(default=False)
    recipient_name: str = Field(..., min_length=1, max_length=100)
    street: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    location: Optional[Location] = Field(None, description="Geographic coordinates")


class PaymentMethod(BaseModel):
    """User payment method model"""
    method_id: str = Field(..., description="Unique payment method identifier")
    type: str = Field(..., description="Payment type: credit_card, debit_card, paypal")
    is_default: bool = Field(default=False)
    last_four: str = Field(..., min_length=4, max_length=4)
    brand: str = Field(..., description="Card brand: visa, mastercard, amex")
    expires_at: str = Field(..., description="Expiration date MM/YY")
    stripe_payment_method_id: Optional[str] = Field(None)


class NotificationPreferences(BaseModel):
    """User notification preferences"""
    email_marketing: bool = Field(default=True)
    order_updates: bool = Field(default=True)
    push_notifications: bool = Field(default=False)


class UserPreferences(BaseModel):
    """User preferences and settings"""
    currency: str = Field(default="USD", min_length=3, max_length=3)
    language: str = Field(default="en", min_length=2, max_length=5)
    notifications: NotificationPreferences = Field(default_factory=NotificationPreferences)


class WishlistItem(BaseModel):
    """Wishlist item model"""
    product_id: str = Field(..., description="Product ObjectId as string")
    variant_id: str = Field(..., description="Product variant identifier")
    added_at: datetime = Field(default_factory=datetime.utcnow)


class Wishlist(BaseModel):
    """User wishlist model"""
    name: str = Field(default="My Wishlist", min_length=1, max_length=100)
    items: List[WishlistItem] = Field(default_factory=list)


class LoyaltyProgram(BaseModel):
    """User loyalty program information"""
    points: int = Field(default=0, ge=0)
    tier: str = Field(default="bronze", description="Loyalty tier: bronze, silver, gold, platinum")
    lifetime_spent: float = Field(default=0.0, ge=0)


class AuthInfo(BaseModel):
    """User authentication information"""
    is_verified: bool = Field(default=False)
    verification_token: Optional[str] = Field(None)
    reset_token: Optional[str] = Field(None)
    last_login: Optional[datetime] = Field(None)
    login_count: int = Field(default=0, ge=0)


class UserProfile(BaseModel):
    """User profile information"""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[datetime] = Field(None)
    avatar: Optional[str] = Field(None, description="Avatar image URL")


class User(Document):
    """User document model"""
    email: Indexed(EmailStr, unique=True) = Field(..., description="User email address")
    password_hash: str = Field(..., description="Hashed password")
    profile: UserProfile = Field(..., description="User profile information")
    addresses: List[Address] = Field(default_factory=list)
    payment_methods: List[PaymentMethod] = Field(default_factory=list)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    wishlists: List[Wishlist] = Field(default_factory=lambda: [Wishlist()])
    loyalty: LoyaltyProgram = Field(default_factory=LoyaltyProgram)
    auth: AuthInfo = Field(default_factory=AuthInfo)
    status: str = Field(default="active", description="User status: active, inactive, suspended")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("email", 1)], unique=True),
            IndexModel([("addresses.location", GEO2D)]),
        ]

    @validator('email')
    def email_must_be_lowercase(cls, v):
        return v.lower()

    def get_default_address(self, address_type: str = "shipping") -> Optional[Address]:
        """Get user's default address of specified type"""
        for address in self.addresses:
            if address.type == address_type and address.is_default:
                return address
        return None

    def get_default_payment_method(self) -> Optional[PaymentMethod]:
        """Get user's default payment method"""
        for payment_method in self.payment_methods:
            if payment_method.is_default:
                return payment_method
        return None

    def add_loyalty_points(self, points: int, amount_spent: float = 0.0):
        """Add loyalty points and update lifetime spending"""
        self.loyalty.points += points
        self.loyalty.lifetime_spent += amount_spent
        
        # Update tier based on lifetime spending
        if self.loyalty.lifetime_spent >= 5000:
            self.loyalty.tier = "platinum"
        elif self.loyalty.lifetime_spent >= 2500:
            self.loyalty.tier = "gold"
        elif self.loyalty.lifetime_spent >= 1000:
            self.loyalty.tier = "silver"
        else:
            self.loyalty.tier = "bronze"


# Request/Response Models

class UserCreate(BaseModel):
    """Schema for user creation"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="User password")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)


class UserUpdate(BaseModel):
    """Schema for user updates"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    preferences: Optional[UserPreferences] = Field(None)


class UserResponse(BaseModel):
    """Schema for user response"""
    id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email address")
    profile: UserProfile = Field(..., description="User profile information")
    preferences: UserPreferences = Field(..., description="User preferences")
    loyalty: LoyaltyProgram = Field(..., description="Loyalty program information")
    status: str = Field(..., description="User status")
    created_at: datetime = Field(..., description="Account creation date")


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")


class PasswordReset(BaseModel):
    """Schema for password reset request"""
    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")


class AddressCreate(BaseModel):
    """Schema for creating a new address"""
    type: str = Field(..., description="Address type: shipping, billing")
    is_default: bool = Field(default=False)
    recipient_name: str = Field(..., min_length=1, max_length=100)
    street: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=2, max_length=2)
    coordinates: Optional[List[float]] = Field(None, description="[longitude, latitude]")


class PaymentMethodCreate(BaseModel):
    """Schema for creating a new payment method"""
    stripe_payment_method_id: str = Field(..., description="Stripe payment method ID")
    is_default: bool = Field(default=False)