"""
Product endpoints
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from beanie import PydanticObjectId
from beanie.operators import In, And, Or, Regex
import math

from app.core.security import get_current_user_id
from app.models.product import (
    Product,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    ProductSearchQuery,
    ProductVariant
)
from app.models.user import User

router = APIRouter()


def convert_product_to_response(product: Product) -> ProductResponse:
    """Convert Product document to ProductResponse"""
    price_range = product.get_price_range()
    return ProductResponse(
        id=str(product.id),
        sku=product.sku,
        name=product.name,
        description=product.description,
        brand=product.brand,
        categories=product.categories,
        base_price=product.base_price,
        variants=product.variants,
        specifications=product.specifications,
        rating_summary=product.rating_summary,
        status=product.status,
        tags=product.tags,
        created_at=product.created_at,
        primary_image=product.get_primary_image(),
        price_range=price_range,
        in_stock=product.is_in_stock()
    )


@router.get("/search", response_model=ProductListResponse)
async def search_products(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Category ID"),
    brand: Optional[str] = Query(None, description="Brand name"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    in_stock: Optional[bool] = Query(None, description="Filter by stock availability"),
    tags: Optional[List[str]] = Query(None, description="Product tags"),
    sort_by: str = Query("relevance", description="Sort by: relevance, price_asc, price_desc, rating, newest"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
) -> Any:
    """
    Search and filter products
    
    Args:
        q: Search query for full-text search
        category: Category ID filter
        brand: Brand name filter
        min_price: Minimum price filter
        max_price: Maximum price filter
        min_rating: Minimum rating filter
        in_stock: Stock availability filter
        tags: Product tags filter
        sort_by: Sort order
        page: Page number
        limit: Items per page
    
    Returns:
        Paginated list of products
    """
    # Build query filters
    filters = [Product.status == "active"]
    
    # Text search
    if q:
        # For full-text search, we'll use MongoDB's text search
        filters.append({"$text": {"$search": q}})
    
    # Category filter
    if category:
        filters.append(In(Product.categories, [category]))
    
    # Brand filter
    if brand:
        filters.append(Product.brand == brand)
    
    # Price range filter
    if min_price is not None or max_price is not None:
        price_conditions = []
        if min_price is not None:
            price_conditions.append({"variants.price": {"$gte": min_price}})
        if max_price is not None:
            price_conditions.append({"variants.price": {"$lte": max_price}})
        
        if price_conditions:
            filters.extend(price_conditions)
    
    # Rating filter
    if min_rating is not None:
        filters.append(Product.rating_summary.average_rating >= min_rating)
    
    # Stock filter
    if in_stock:
        filters.append({"variants.inventory.quantity": {"$gt": 0}})
    
    # Tags filter
    if tags:
        filters.append(In(Product.tags, tags))
    
    # Build aggregation pipeline for complex queries
    pipeline = []
    
    # Match stage
    if filters:
        if len(filters) == 1:
            match_filter = filters[0]
        else:
            match_filter = {"$and": filters}
        pipeline.append({"$match": match_filter})
    
    # Add text score for relevance sorting
    if q:
        pipeline.append({
            "$addFields": {
                "score": {"$meta": "textScore"}
            }
        })
    
    # Add computed fields
    pipeline.append({
        "$addFields": {
            "min_price": {"$min": "$variants.price"},
            "max_price": {"$max": "$variants.price"},
            "total_inventory": {"$sum": "$variants.inventory.quantity"}
        }
    })
    
    # Sort stage
    sort_stage = {}
    if sort_by == "relevance" and q:
        sort_stage = {"score": {"$meta": "textScore"}}
    elif sort_by == "price_asc":
        sort_stage = {"min_price": 1}
    elif sort_by == "price_desc":
        sort_stage = {"min_price": -1}
    elif sort_by == "rating":
        sort_stage = {"rating_summary.average_rating": -1}
    elif sort_by == "newest":
        sort_stage = {"created_at": -1}
    else:  # default to newest
        sort_stage = {"created_at": -1}
    
    if sort_stage:
        pipeline.append({"$sort": sort_stage})
    
    # Count total documents
    count_pipeline = pipeline + [{"$count": "total"}]
    count_result = await Product.aggregate(count_pipeline).to_list()
    total = count_result[0]["total"] if count_result else 0
    
    # Add pagination
    skip = (page - 1) * limit
    pipeline.extend([
        {"$skip": skip},
        {"$limit": limit}
    ])
    
    # Execute query
    products_cursor = Product.aggregate(pipeline)
    products_data = await products_cursor.to_list()
    
    # Convert to Product objects and then to response format
    products = []
    for product_data in products_data:
        product = Product(**product_data)
        products.append(convert_product_to_response(product))
    
    total_pages = math.ceil(total / limit)
    
    return ProductListResponse(
        products=products,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str) -> Any:
    """
    Get product by ID
    
    Args:
        product_id: Product ID
    
    Returns:
        Product details
    
    Raises:
        HTTPException: If product not found
    """
    try:
        product = await Product.get(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        return convert_product_to_response(product)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Create a new product
    
    Args:
        product_data: Product creation data
        current_user_id: Current user ID
    
    Returns:
        Created product
    
    Raises:
        HTTPException: If SKU already exists
    """
    # Check if any variant SKUs already exist
    existing_skus = []
    for variant in product_data.variants:
        existing_product = await Product.find_one({"variants.sku": variant.sku})
        if existing_product:
            existing_skus.append(variant.sku)
    
    if existing_skus:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SKUs already exist: {', '.join(existing_skus)}"
        )
    
    # Generate unique product SKU
    import uuid
    product_sku = f"PROD-{str(uuid.uuid4())[:8].upper()}"
    
    # Calculate base price from variants
    variant_prices = [v.price for v in product_data.variants]
    base_price = min(variant_prices) if variant_prices else 0
    
    # Convert ProductVariantCreate to ProductVariant
    from app.models.product import ProductVariant, InventoryInfo
    variants = []
    for i, variant_data in enumerate(product_data.variants):
        variant = ProductVariant(
            variant_id=f"VAR-{i+1:03d}",
            name=variant_data.name,
            sku=variant_data.sku,
            price=variant_data.price,
            attributes=variant_data.attributes,
            inventory=InventoryInfo(
                quantity=variant_data.quantity,
                warehouse_location=variant_data.warehouse_location
            ),
            images=variant_data.images
        )
        variants.append(variant)
    
    # Create product
    product = Product(
        sku=product_sku,
        name=product_data.name,
        description=product_data.description,
        brand=product_data.brand,
        categories=product_data.categories,
        base_price=base_price,
        variants=variants,
        specifications=product_data.specifications,
        search_keywords=product_data.search_keywords,
        tags=product_data.tags,
        created_by=current_user_id
    )
    
    await product.save()
    
    return convert_product_to_response(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Update product
    
    Args:
        product_id: Product ID
        product_data: Product update data
        current_user_id: Current user ID
    
    Returns:
        Updated product
    
    Raises:
        HTTPException: If product not found
    """
    product = await Product.get(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Update fields
    update_data = product_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    from datetime import datetime
    product.updated_at = datetime.utcnow()
    
    await product.save()
    
    return convert_product_to_response(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Delete product (soft delete by setting status to inactive)
    
    Args:
        product_id: Product ID
        current_user_id: Current user ID
    
    Raises:
        HTTPException: If product not found
    """
    product = await Product.get(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    product.status = "inactive"
    from datetime import datetime
    product.updated_at = datetime.utcnow()
    
    await product.save()


@router.patch("/{product_id}/inventory", response_model=ProductResponse)
async def update_product_inventory(
    product_id: str,
    variant_id: str,
    quantity: int,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Update product variant inventory
    
    Args:
        product_id: Product ID
        variant_id: Variant ID
        quantity: New quantity
        current_user_id: Current user ID
    
    Returns:
        Updated product
    
    Raises:
        HTTPException: If product or variant not found
    """
    product = await Product.get(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Find variant
    variant = product.get_variant_by_id(variant_id)
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found"
        )
    
    # Update inventory
    variant.inventory.quantity = quantity
    from datetime import datetime
    product.updated_at = datetime.utcnow()
    
    await product.save()
    
    return convert_product_to_response(product)


@router.get("/{product_id}/recommendations", response_model=ProductListResponse)
async def get_product_recommendations(
    product_id: str,
    limit: int = Query(6, ge=1, le=20, description="Number of recommendations")
) -> Any:
    """
    Get product recommendations based on categories and ratings
    
    Args:
        product_id: Product ID
        limit: Number of recommendations
    
    Returns:
        List of recommended products
    """
    # Get the current product
    product = await Product.get(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Find similar products by categories
    similar_products = await Product.find(
        And(
            In(Product.categories, product.categories),
            Product.id != product.id,
            Product.status == "active",
            Product.rating_summary.average_rating >= 3.0
        )
    ).sort(-Product.rating_summary.average_rating).limit(limit).to_list()
    
    # Convert to response format
    recommendations = [convert_product_to_response(p) for p in similar_products]
    
    return ProductListResponse(
        products=recommendations,
        total=len(recommendations),
        page=1,
        limit=limit,
        total_pages=1
    )