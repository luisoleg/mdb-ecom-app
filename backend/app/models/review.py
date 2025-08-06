"""
Product Review model
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from beanie import Document, Indexed
from pymongo import IndexModel
from app.models.product import ProductImage


class Review(Document):
    """Product review document model"""
    product_id: str = Field(..., description="Product ID")
    variant_id: Optional[str] = Field(None, description="Specific variant ID (optional)")
    user_id: str = Field(..., description="Reviewer user ID")
    order_id: Optional[str] = Field(None, description="Order ID if this is a verified purchase")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    title: str = Field(..., min_length=1, max_length=100, description="Review title")
    content: str = Field(..., min_length=10, max_length=2000, description="Review content")
    pros: List[str] = Field(default_factory=list, description="List of pros")
    cons: List[str] = Field(default_factory=list, description="List of cons")
    verified_purchase: bool = Field(default=False, description="Whether this is a verified purchase")
    helpful_votes: int = Field(default=0, ge=0, description="Number of helpful votes")
    total_votes: int = Field(default=0, ge=0, description="Total number of votes")
    images: List[ProductImage] = Field(default_factory=list, description="Review images")
    status: str = Field(default="pending", description="Review status: pending, approved, rejected")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reviews"
        indexes = [
            IndexModel([("product_id", 1), ("status", 1), ("created_at", -1)]),
            IndexModel([("user_id", 1), ("created_at", -1)]),
            IndexModel([("rating", 1)]),
            IndexModel([("helpful_votes", -1)]),
        ]

    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

    def calculate_helpfulness_score(self) -> float:
        """Calculate helpfulness score as percentage"""
        if self.total_votes == 0:
            return 0.0
        return (self.helpful_votes / self.total_votes) * 100

    def add_helpful_vote(self, is_helpful: bool):
        """Add a helpful vote"""
        self.total_votes += 1
        if is_helpful:
            self.helpful_votes += 1
        self.updated_at = datetime.utcnow()


class ReviewVote(Document):
    """Review vote tracking to prevent duplicate votes"""
    review_id: str = Field(..., description="Review ID")
    user_id: str = Field(..., description="User ID who voted")
    is_helpful: bool = Field(..., description="Whether vote was helpful")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "review_votes"
        indexes = [
            IndexModel([("review_id", 1), ("user_id", 1)], unique=True),
        ]


# Request/Response Models

class ReviewCreate(BaseModel):
    """Schema for creating a review"""
    product_id: str = Field(..., description="Product ID")
    variant_id: Optional[str] = Field(None, description="Variant ID (optional)")
    order_id: Optional[str] = Field(None, description="Order ID for verified purchases")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    title: str = Field(..., min_length=1, max_length=100, description="Review title")
    content: str = Field(..., min_length=10, max_length=2000, description="Review content")
    pros: List[str] = Field(default_factory=list, description="List of pros")
    cons: List[str] = Field(default_factory=list, description="List of cons")


class ReviewUpdate(BaseModel):
    """Schema for updating a review"""
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5")
    title: Optional[str] = Field(None, min_length=1, max_length=100, description="Review title")
    content: Optional[str] = Field(None, min_length=10, max_length=2000, description="Review content")
    pros: Optional[List[str]] = Field(None, description="List of pros")
    cons: Optional[List[str]] = Field(None, description="List of cons")


class ReviewVoteCreate(BaseModel):
    """Schema for voting on review helpfulness"""
    is_helpful: bool = Field(..., description="Whether the review was helpful")


class ReviewResponse(BaseModel):
    """Schema for review response"""
    id: str = Field(..., description="Review ID")
    product_id: str = Field(..., description="Product ID")
    variant_id: Optional[str] = Field(None, description="Variant ID")
    user_id: str = Field(..., description="User ID")
    rating: int = Field(..., description="Rating")
    title: str = Field(..., description="Review title")
    content: str = Field(..., description="Review content")
    pros: List[str] = Field(..., description="Pros list")
    cons: List[str] = Field(..., description="Cons list")
    verified_purchase: bool = Field(..., description="Verified purchase status")
    helpful_votes: int = Field(..., description="Helpful votes count")
    total_votes: int = Field(..., description="Total votes count")
    helpfulness_score: float = Field(..., description="Helpfulness percentage")
    images: List[ProductImage] = Field(..., description="Review images")
    status: str = Field(..., description="Review status")
    created_at: datetime = Field(..., description="Creation date")
    updated_at: datetime = Field(..., description="Last update date")
    # These fields would be populated from user lookup
    reviewer_name: Optional[str] = Field(None, description="Reviewer name")
    reviewer_avatar: Optional[str] = Field(None, description="Reviewer avatar URL")


class ReviewListResponse(BaseModel):
    """Schema for review list response"""
    reviews: List[ReviewResponse] = Field(..., description="List of reviews")
    total: int = Field(..., description="Total number of reviews")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    average_rating: float = Field(..., description="Average rating for the product")
    rating_distribution: dict = Field(..., description="Rating distribution")


class ReviewStatsResponse(BaseModel):
    """Schema for review statistics response"""
    total_reviews: int = Field(..., description="Total number of reviews")
    average_rating: float = Field(..., description="Average rating")
    rating_distribution: dict = Field(..., description="Distribution of ratings")
    verified_purchases_percentage: float = Field(..., description="Percentage of verified purchases")


class ReviewQuery(BaseModel):
    """Schema for review query parameters"""
    product_id: Optional[str] = Field(None, description="Filter by product ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Filter by rating")
    verified_only: Optional[bool] = Field(None, description="Show only verified purchases")
    status: Optional[str] = Field(None, description="Filter by status")
    sort_by: Optional[str] = Field("newest", description="Sort by: newest, oldest, rating_high, rating_low, helpful")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(10, ge=1, le=50, description="Items per page")