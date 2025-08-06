"""
Product Categories endpoints
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.security import get_current_user_id
from app.models.product import (
    Category,
    CategoryCreate,
    CategoryResponse,
    SEOInfo,
    ProductImage
)

router = APIRouter()


@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    parent_id: Optional[str] = Query(None, description="Filter by parent category ID"),
    level: Optional[int] = Query(None, description="Filter by category level")
) -> Any:
    """Get product categories"""
    query = Category.is_active == True
    
    if parent_id:
        query = query & (Category.parent_id == parent_id)
    elif parent_id is None and level == 0:
        query = query & (Category.parent_id == None)
    
    if level is not None:
        query = query & (Category.level == level)
    
    categories = await Category.find(query).sort(+Category.sort_order).to_list()
    
    return [
        CategoryResponse(
            id=str(cat.id),
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            parent_id=cat.parent_id,
            level=cat.level,
            path=cat.path,
            children=cat.children,
            image=cat.image,
            is_active=cat.is_active
        ) for cat in categories
    ]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str) -> Any:
    """Get category by ID"""
    category = await Category.get(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return CategoryResponse(
        id=str(category.id),
        name=category.name,
        slug=category.slug,
        description=category.description,
        parent_id=category.parent_id,
        level=category.level,
        path=category.path,
        children=category.children,
        image=category.image,
        is_active=category.is_active
    )


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Create new category (admin only)"""
    # Check if slug already exists
    existing = await Category.find_one(Category.slug == category_data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category slug already exists"
        )
    
    # Get parent category if specified
    parent_category = None
    level = 0
    path = f"/{category_data.slug}"
    
    if category_data.parent_id:
        parent_category = await Category.get(category_data.parent_id)
        if not parent_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )
        level = parent_category.level + 1
        path = f"{parent_category.path}/{category_data.slug}"
    
    # Create category image if provided
    image = None
    if category_data.image_url:
        image = ProductImage(
            url=category_data.image_url,
            alt=f"{category_data.name} category image",
            is_primary=True
        )
    
    # Create category
    category = Category(
        name=category_data.name,
        slug=category_data.slug,
        description=category_data.description,
        parent_id=category_data.parent_id,
        level=level,
        path=path,
        image=image,
        sort_order=category_data.sort_order
    )
    
    await category.save()
    
    # Update parent's children list
    if parent_category:
        parent_category.children.append(str(category.id))
        await parent_category.save()
    
    return CategoryResponse(
        id=str(category.id),
        name=category.name,
        slug=category.slug,
        description=category.description,
        parent_id=category.parent_id,
        level=category.level,
        path=category.path,
        children=category.children,
        image=category.image,
        is_active=category.is_active
    )