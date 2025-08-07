"""
Physical Stores endpoints (Geospatial features)
"""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user_id
from app.models.product import Product
from app.models.store import (
    Location,
    NearbyStoreResponse,
    Store,
    StoreCreate,
    StoreHours,
    StoreInventoryUpdate,
    StoreListResponse,
    StoreResponse,
)

router = APIRouter()


def populate_store_response(
    store: Store, distance: Optional[float] = None
) -> StoreResponse:
    """Convert Store document to StoreResponse"""
    return StoreResponse(
        id=str(store.id),
        store_id=store.store_id,
        name=store.name,
        address=store.address,
        location=store.location,
        contact=store.contact,
        hours=store.hours,
        services=store.services,
        manager_id=store.manager_id,
        capacity=store.capacity,
        is_active=store.is_active,
        is_open_now=store.is_open_now(),
        distance=distance,
        available_products=[
            item.product_id for item in store.inventory if item.quantity > 0
        ],
        created_at=store.created_at,
    )


@router.get("/search", response_model=StoreListResponse)
async def search_nearby_stores(
    latitude: float = Query(
        ..., ge=-90, le=90, description="Search center latitude"
    ),
    longitude: float = Query(
        ..., ge=-180, le=180, description="Search center longitude"
    ),
    radius: int = Query(
        10000, ge=1, le=100000, description="Search radius in meters"
    ),
    product_id: Optional[str] = Query(
        None, description="Filter stores with specific product"
    ),
    variant_id: Optional[str] = Query(
        None, description="Filter stores with specific variant"
    ),
    services: Optional[List[str]] = Query(
        None, description="Filter by available services"
    ),
    open_now: Optional[bool] = Query(
        None, description="Filter by stores open now"
    ),
    limit: int = Query(
        10, ge=1, le=50, description="Maximum number of results"
    ),
) -> Any:
    """
    Search for nearby stores using geospatial queries

    This endpoint demonstrates MongoDB's geospatial capabilities with $geoNear
    aggregation
    """

    # Build aggregation pipeline for geospatial search
    pipeline = [
        {
            "$geoNear": {
                "near": {
                    "type": "Point",
                    "coordinates": [longitude, latitude],
                },
                "distanceField": "distance",
                "maxDistance": radius,
                "spherical": True,
                "query": {"is_active": True},
            }
        }
    ]

    # Add product/variant filter if specified
    if product_id and variant_id:
        pipeline.append(
            {
                "$match": {
                    "inventory": {
                        "$elemMatch": {
                            "product_id": product_id,
                            "variant_id": variant_id,
                            "quantity": {"$gt": 0},
                        }
                    }
                }
            }
        )
    elif product_id:
        pipeline.append(
            {
                "$match": {
                    "inventory.product_id": product_id,
                    "inventory.quantity": {"$gt": 0},
                }
            }
        )

    # Add services filter
    if services:
        pipeline.append({"$match": {"services": {"$in": services}}})

    # Add computed fields
    pipeline.append(
        {
            "$addFields": {
                "is_open_now": {
                    "$let": {
                        "vars": {
                            "now": "$$NOW",
                            "dayOfWeek": {"$dayOfWeek": "$$NOW"},
                        },
                        # Simplified for demo - complex logic needed for hours
                        "in": True,
                    }
                }
            }
        }
    )

    # Filter by open_now if specified
    if open_now is not None:
        pipeline.append({"$match": {"is_open_now": open_now}})

    # Sort by distance and limit results
    pipeline.extend([{"$sort": {"distance": 1}}, {"$limit": limit}])

    # Execute aggregation
    stores_data = await Store.aggregate(pipeline).to_list()

    # Convert to response format
    stores = []
    for store_data in stores_data:
        distance = store_data.get("distance", 0)
        store = Store(
            **{k: v for k, v in store_data.items() if k != "distance"}
        )
        store_response = populate_store_response(store, distance)
        stores.append(store_response)

    return StoreListResponse(
        stores=stores,
        total=len(stores),
        search_center={"latitude": latitude, "longitude": longitude},
        search_radius=radius,
    )


@router.get("/nearby/{product_id}", response_model=NearbyStoreResponse)
async def find_stores_with_product(
    product_id: str,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    variant_id: Optional[str] = Query(None),
    radius: int = Query(
        50000, ge=1, le=100000, description="Search radius in meters"
    ),
    limit: int = Query(10, ge=1, le=20),
) -> Any:
    """
    Find nearby stores that have a specific product in stock

    This demonstrates advanced geospatial queries combined with inventory filtering
    """

    # Verify product exists
    product = await Product.get(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Build aggregation pipeline
    pipeline = [
        {
            "$geoNear": {
                "near": {
                    "type": "Point",
                    "coordinates": [longitude, latitude],
                },
                "distanceField": "distance",
                "maxDistance": radius,
                "spherical": True,
                "query": {
                    "is_active": True,
                    "inventory": {
                        "$elemMatch": {
                            "product_id": product_id,
                            "quantity": {"$gt": 0},
                        }
                    },
                },
            }
        }
    ]

    # Add variant filter if specified
    if variant_id:
        pipeline[0]["$geoNear"]["query"]["inventory"]["$elemMatch"][
            "variant_id"
        ] = variant_id

    # Add inventory details for the specific product
    pipeline.append(
        {
            "$addFields": {
                "product_inventory": {
                    "$filter": {
                        "input": "$inventory",
                        "cond": {
                            "$and": [
                                {"$eq": ["$$this.product_id", product_id]},
                                {"$gt": ["$$this.quantity", 0]},
                            ]
                            + (
                                [{"$eq": ["$$this.variant_id", variant_id]}]
                                if variant_id
                                else []
                            )
                        },
                    }
                }
            }
        }
    )

    pipeline.extend([{"$sort": {"distance": 1}}, {"$limit": limit}])

    # Execute query
    stores_data = await Store.aggregate(pipeline).to_list()

    # Convert to response format
    stores = []
    for store_data in stores_data:
        distance = store_data.get("distance", 0)
        # Remove computed fields before creating Store object
        clean_data = {
            k: v
            for k, v in store_data.items()
            if k not in ["distance", "product_inventory"]
        }
        store = Store(**clean_data)
        store_response = populate_store_response(store, distance)
        stores.append(store_response)

    return NearbyStoreResponse(
        product_id=product_id,
        variant_id=variant_id,
        stores=stores,
        total_stores=len(stores),
    )


@router.get("/", response_model=StoreListResponse)
async def get_all_stores(
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    is_active: bool = Query(True, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """Get all stores with optional filtering"""

    # Build query
    query = Store.is_active == is_active

    if city:
        query = query & (Store.address.city == city)
    if state:
        query = query & (Store.address.state == state)

    stores = await Store.find(query).limit(limit).to_list()

    store_responses = [populate_store_response(store) for store in stores]

    return StoreListResponse(
        stores=store_responses, total=len(store_responses)
    )


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(store_id: str) -> Any:
    """Get store by ID"""

    store = await Store.get(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    return populate_store_response(store)


@router.post(
    "/", response_model=StoreResponse, status_code=status.HTTP_201_CREATED
)
async def create_store(
    store_data: StoreCreate,
    current_user_id: str = Depends(get_current_user_id),
) -> Any:
    """Create a new store (admin only)"""

    # Check if store_id already exists
    existing_store = await Store.find_one(
        Store.store_id == store_data.store_id
    )
    if existing_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store ID already exists",
        )

    # Create location from coordinates
    location = Location(coordinates=store_data.coordinates)

    # Convert hours from create format to dict
    hours_dict = {}
    if store_data.hours:
        hours_data = store_data.hours.dict(exclude_unset=True)
        for day, hours in hours_data.items():
            if hours:
                hours_dict[day] = StoreHours(**hours)

    # Create store
    store = Store(
        store_id=store_data.store_id,
        name=store_data.name,
        address=store_data.address,
        location=location,
        contact=store_data.contact or {},
        hours=hours_dict,
        services=store_data.services,
        manager_id=store_data.manager_id,
        capacity=store_data.capacity,
    )

    await store.save()

    return populate_store_response(store)


@router.patch("/{store_id}/inventory", response_model=StoreResponse)
async def update_store_inventory(
    store_id: str,
    inventory_update: StoreInventoryUpdate,
    current_user_id: str = Depends(get_current_user_id),
) -> Any:
    """Update store inventory for a specific product"""

    store = await Store.get(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Store not found"
        )

    # Verify product exists
    product = await Product.get(inventory_update.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Update inventory
    store.update_inventory(
        product_id=inventory_update.product_id,
        variant_id=inventory_update.variant_id,
        quantity=inventory_update.quantity,
    )

    await store.save()

    return populate_store_response(store)
