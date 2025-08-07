"""
Product and Category models
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field
from pymongo import TEXT, IndexModel


class ProductImage(BaseModel):
    """Product image model"""

    url: str = Field(..., description="Image URL")
    alt: str = Field(..., description="Alt text for accessibility")
    is_primary: bool = Field(
        default=False, description="Whether this is the primary image"
    )


class InventoryInfo(BaseModel):
    """Inventory information for product variants"""

    quantity: int = Field(..., ge=0, description="Available quantity")
    reserved: int = Field(default=0, ge=0, description="Reserved quantity")
    warehouse_location: Optional[str] = Field(
        None, description="Warehouse location code"
    )


class ProductVariant(BaseModel):
    """Product variant model"""

    variant_id: str = Field(..., description="Unique variant identifier")
    name: str = Field(
        ..., min_length=1, max_length=200, description="Variant name"
    )
    sku: str = Field(..., description="Stock Keeping Unit")
    price: float = Field(..., gt=0, description="Variant price")
    attributes: Dict[str, str] = Field(
        default_factory=dict,
        description="Variant attributes (color, size, etc.)",
    )
    inventory: InventoryInfo = Field(..., description="Inventory information")
    images: List[ProductImage] = Field(
        default_factory=list, description="Variant-specific images"
    )
    is_active: bool = Field(
        default=True, description="Whether variant is active"
    )


class SEOInfo(BaseModel):
    """SEO information for products"""

    meta_title: Optional[str] = Field(
        None, max_length=60, description="Meta title"
    )
    meta_description: Optional[str] = Field(
        None, max_length=160, description="Meta description"
    )
    keywords: List[str] = Field(
        default_factory=list, description="SEO keywords"
    )


class RatingDistribution(BaseModel):
    """Rating distribution model"""

    five_star: int = Field(default=0, ge=0, alias="5")
    four_star: int = Field(default=0, ge=0, alias="4")
    three_star: int = Field(default=0, ge=0, alias="3")
    two_star: int = Field(default=0, ge=0, alias="2")
    one_star: int = Field(default=0, ge=0, alias="1")


class RatingSummary(BaseModel):
    """Product rating summary"""

    average_rating: float = Field(
        default=0.0, ge=0, le=5, description="Average rating"
    )
    total_reviews: int = Field(
        default=0, ge=0, description="Total number of reviews"
    )
    rating_distribution: RatingDistribution = Field(
        default_factory=RatingDistribution
    )


class Product(Document):
    """Product document model"""

    sku: Indexed(str, unique=True) = Field(..., description="Product SKU")
    name: str = Field(
        ..., min_length=1, max_length=200, description="Product name"
    )
    description: str = Field(
        ..., min_length=1, description="Product description"
    )
    brand: str = Field(
        ..., min_length=1, max_length=100, description="Product brand"
    )
    categories: List[str] = Field(..., description="Category IDs")
    base_price: float = Field(
        ..., gt=0, description="Base price for the product"
    )
    variants: List[ProductVariant] = Field(
        ..., min_items=1, description="Product variants"
    )
    specifications: Dict[str, Any] = Field(
        default_factory=dict, description="Product specifications"
    )
    seo: SEOInfo = Field(
        default_factory=SEOInfo, description="SEO information"
    )
    search_keywords: List[str] = Field(
        default_factory=list, description="Search keywords"
    )
    rating_summary: RatingSummary = Field(default_factory=RatingSummary)
    status: str = Field(
        default="active",
        description="Product status: active, inactive, discontinued",
    )
    tags: List[str] = Field(default_factory=list, description="Product tags")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="User ID who created the product")

    class Settings:
        name = "products"
        indexes = [
            IndexModel(
                [
                    ("name", TEXT),
                    ("description", TEXT),
                    ("search_keywords", TEXT),
                    ("brand", TEXT),
                ],
                name="text_search_index",
            ),
            IndexModel([("categories", 1), ("status", 1)]),
            IndexModel([("variants.price", 1)]),
            IndexModel([("rating_summary.average_rating", -1)]),
            IndexModel([("variants.sku", 1)], unique=True),
        ]

    def get_variant_by_id(self, variant_id: str) -> Optional[ProductVariant]:
        """Get variant by ID"""
        for variant in self.variants:
            if variant.variant_id == variant_id:
                return variant
        return None

    def get_primary_image(self) -> Optional[str]:
        """Get primary product image URL"""
        for variant in self.variants:
            for image in variant.images:
                if image.is_primary:
                    return image.url

        # If no primary image found, return first available image
        for variant in self.variants:
            if variant.images:
                return variant.images[0].url

        return None

    def get_price_range(self) -> tuple[float, float]:
        """Get price range for all variants"""
        prices = [
            variant.price for variant in self.variants if variant.is_active
        ]
        if not prices:
            return (0.0, 0.0)
        return (min(prices), max(prices))

    def get_total_inventory(self) -> int:
        """Get total inventory across all variants"""
        return sum(variant.inventory.quantity for variant in self.variants)

    def is_in_stock(self) -> bool:
        """Check if product has any stock available"""
        return any(
            variant.inventory.quantity > 0
            for variant in self.variants
            if variant.is_active
        )

    def update_rating(self, new_rating: float, increment_reviews: bool = True):
        """Update product rating summary"""
        if increment_reviews:
            current_total = self.rating_summary.total_reviews
            current_avg = self.rating_summary.average_rating

            # Calculate new average
            new_total = current_total + 1
            new_avg = ((current_avg * current_total) + new_rating) / new_total

            self.rating_summary.average_rating = round(new_avg, 2)
            self.rating_summary.total_reviews = new_total

            # Update rating distribution
            rating_int = int(round(new_rating))
            if rating_int == 5:
                self.rating_summary.rating_distribution.five_star += 1
            elif rating_int == 4:
                self.rating_summary.rating_distribution.four_star += 1
            elif rating_int == 3:
                self.rating_summary.rating_distribution.three_star += 1
            elif rating_int == 2:
                self.rating_summary.rating_distribution.two_star += 1
            elif rating_int == 1:
                self.rating_summary.rating_distribution.one_star += 1


class Category(Document):
    """Product category model"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Category name"
    )
    slug: Indexed(str, unique=True) = Field(
        ..., description="URL-friendly category slug"
    )
    description: Optional[str] = Field(
        None, description="Category description"
    )
    parent_id: Optional[str] = Field(None, description="Parent category ID")
    level: int = Field(default=0, ge=0, description="Category hierarchy level")
    path: str = Field(
        ..., description="Category path (e.g., /electronics/audio)"
    )
    children: List[str] = Field(
        default_factory=list, description="Child category IDs"
    )
    image: Optional[ProductImage] = Field(None, description="Category image")
    seo: SEOInfo = Field(
        default_factory=SEOInfo, description="SEO information"
    )
    sort_order: int = Field(default=0, description="Sort order for display")
    is_active: bool = Field(
        default=True, description="Whether category is active"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "categories"
        indexes = [
            IndexModel([("slug", 1)], unique=True),
            IndexModel([("parent_id", 1)]),
            IndexModel([("level", 1)]),
        ]

    def get_full_path(self) -> str:
        """Get full category path"""
        return self.path


# Request/Response Models


class CategoryCreate(BaseModel):
    """Schema for category creation"""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None)
    parent_id: Optional[str] = Field(None)
    image_url: Optional[str] = Field(None)
    sort_order: int = Field(default=0)


class CategoryResponse(BaseModel):
    """Schema for category response"""

    id: str = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    slug: str = Field(..., description="Category slug")
    description: Optional[str] = Field(
        None, description="Category description"
    )
    parent_id: Optional[str] = Field(None, description="Parent category ID")
    level: int = Field(..., description="Category level")
    path: str = Field(..., description="Category path")
    children: List[str] = Field(..., description="Child category IDs")
    image: Optional[ProductImage] = Field(None, description="Category image")
    is_active: bool = Field(..., description="Category status")


class ProductVariantCreate(BaseModel):
    """Schema for creating product variants"""

    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    attributes: Dict[str, str] = Field(default_factory=dict)
    quantity: int = Field(..., ge=0)
    warehouse_location: Optional[str] = Field(None)
    images: List[ProductImage] = Field(default_factory=list)


class ProductCreate(BaseModel):
    """Schema for product creation"""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    brand: str = Field(..., min_length=1, max_length=100)
    categories: List[str] = Field(..., min_items=1)
    variants: List[ProductVariantCreate] = Field(..., min_items=1)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    search_keywords: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """Schema for product updates"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    brand: Optional[str] = Field(None, min_length=1, max_length=100)
    categories: Optional[List[str]] = Field(None)
    specifications: Optional[Dict[str, Any]] = Field(None)
    search_keywords: Optional[List[str]] = Field(None)
    tags: Optional[List[str]] = Field(None)
    status: Optional[str] = Field(None)


class ProductSearchQuery(BaseModel):
    """Schema for product search queries"""

    q: Optional[str] = Field(None, description="Search query")
    category: Optional[str] = Field(None, description="Category ID")
    brand: Optional[str] = Field(None, description="Brand name")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    min_rating: Optional[float] = Field(
        None, ge=0, le=5, description="Minimum rating"
    )
    in_stock: Optional[bool] = Field(
        None, description="Filter by stock availability"
    )
    tags: Optional[List[str]] = Field(None, description="Product tags")
    sort_by: Optional[str] = Field(
        "relevance",
        description="Sort by: relevance, price_asc, price_desc, rating, newest",
    )
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")


class ProductResponse(BaseModel):
    """Schema for product response"""

    id: str = Field(..., description="Product ID")
    sku: str = Field(..., description="Product SKU")
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    brand: str = Field(..., description="Product brand")
    categories: List[str] = Field(..., description="Category IDs")
    base_price: float = Field(..., description="Base price")
    variants: List[ProductVariant] = Field(..., description="Product variants")
    specifications: Dict[str, Any] = Field(
        ..., description="Product specifications"
    )
    rating_summary: RatingSummary = Field(..., description="Rating summary")
    status: str = Field(..., description="Product status")
    tags: List[str] = Field(..., description="Product tags")
    created_at: datetime = Field(..., description="Creation date")
    primary_image: Optional[str] = Field(None, description="Primary image URL")
    price_range: tuple[float, float] = Field(..., description="Price range")
    in_stock: bool = Field(..., description="Stock availability")


class ProductListResponse(BaseModel):
    """Schema for product list response"""

    products: List[ProductResponse] = Field(
        ..., description="List of products"
    )
    total: int = Field(..., description="Total number of products")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
