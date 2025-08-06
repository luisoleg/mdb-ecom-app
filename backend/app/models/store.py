"""
Physical Store model for geospatial features
"""
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator
from beanie import Document, Indexed
from pymongo import IndexModel, GEO2D
from app.models.user import Location


class StoreHours(BaseModel):
    """Store operating hours for a specific day"""
    open: str = Field(..., description="Opening time in HH:MM format")
    close: str = Field(..., description="Closing time in HH:MM format")
    is_closed: bool = Field(default=False, description="Whether store is closed this day")


class StoreContact(BaseModel):
    """Store contact information"""
    phone: Optional[str] = Field(None, description="Store phone number")
    email: Optional[str] = Field(None, description="Store email address")
    website: Optional[str] = Field(None, description="Store website URL")


class StoreAddress(BaseModel):
    """Store address information"""
    street: str = Field(..., min_length=1, max_length=200, description="Street address")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    state: str = Field(..., min_length=1, max_length=100, description="State/Province")
    postal_code: str = Field(..., min_length=1, max_length=20, description="Postal code")
    country: str = Field(..., min_length=2, max_length=2, description="Country code")


class StoreInventoryItem(BaseModel):
    """Store inventory item"""
    product_id: str = Field(..., description="Product ID")
    variant_id: str = Field(..., description="Variant ID")
    quantity: int = Field(..., ge=0, description="Available quantity")
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class Store(Document):
    """Physical store document model"""
    store_id: Indexed(str, unique=True) = Field(..., description="Unique store identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Store name")
    address: StoreAddress = Field(..., description="Store address")
    location: Location = Field(..., description="Store geographic coordinates")
    contact: StoreContact = Field(default_factory=StoreContact, description="Contact information")
    hours: Dict[str, StoreHours] = Field(..., description="Operating hours by day of week")
    services: List[str] = Field(default_factory=list, description="Available services")
    inventory: List[StoreInventoryItem] = Field(default_factory=list, description="Store inventory")
    manager_id: Optional[str] = Field(None, description="Store manager user ID")
    capacity: Optional[int] = Field(None, description="Store capacity/size")
    is_active: bool = Field(default=True, description="Whether store is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "stores"
        indexes = [
            IndexModel([("location", GEO2D)]),
            IndexModel([("store_id", 1)], unique=True),
            IndexModel([("is_active", 1)]),
        ]

    def get_inventory_for_product(self, product_id: str, variant_id: str) -> Optional[StoreInventoryItem]:
        """Get inventory information for a specific product variant"""
        for item in self.inventory:
            if item.product_id == product_id and item.variant_id == variant_id:
                return item
        return None

    def update_inventory(self, product_id: str, variant_id: str, quantity: int):
        """Update inventory for a specific product variant"""
        for item in self.inventory:
            if item.product_id == product_id and item.variant_id == variant_id:
                item.quantity = quantity
                item.last_updated = datetime.utcnow()
                self.updated_at = datetime.utcnow()
                return
        
        # If item not found, add new inventory item
        new_item = StoreInventoryItem(
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity
        )
        self.inventory.append(new_item)
        self.updated_at = datetime.utcnow()

    def is_open_now(self) -> bool:
        """Check if store is currently open"""
        from datetime import datetime
        now = datetime.now()
        day_name = now.strftime("%A").lower()
        
        if day_name not in self.hours:
            return False
        
        day_hours = self.hours[day_name]
        if day_hours.is_closed:
            return False
        
        current_time = now.strftime("%H:%M")
        return day_hours.open <= current_time <= day_hours.close

    def get_distance_from(self, longitude: float, latitude: float) -> float:
        """Calculate distance from given coordinates (in meters)"""
        from math import radians, cos, sin, asin, sqrt
        
        # Haversine formula
        lon1, lat1 = radians(longitude), radians(latitude)
        lon2, lat2 = radians(self.location.coordinates[0]), radians(self.location.coordinates[1])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371000  # Radius of earth in meters
        
        return c * r


# Request/Response Models

class StoreHoursCreate(BaseModel):
    """Schema for creating store hours"""
    monday: Optional[StoreHours] = Field(None)
    tuesday: Optional[StoreHours] = Field(None)
    wednesday: Optional[StoreHours] = Field(None)
    thursday: Optional[StoreHours] = Field(None)
    friday: Optional[StoreHours] = Field(None)
    saturday: Optional[StoreHours] = Field(None)
    sunday: Optional[StoreHours] = Field(None)


class StoreCreate(BaseModel):
    """Schema for creating a store"""
    store_id: str = Field(..., min_length=1, description="Unique store identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Store name")
    address: StoreAddress = Field(..., description="Store address")
    coordinates: List[float] = Field(..., description="[longitude, latitude]")
    contact: Optional[StoreContact] = Field(None, description="Contact information")
    hours: StoreHoursCreate = Field(..., description="Operating hours")
    services: List[str] = Field(default_factory=list, description="Available services")
    manager_id: Optional[str] = Field(None, description="Store manager user ID")
    capacity: Optional[int] = Field(None, description="Store capacity")


class StoreUpdate(BaseModel):
    """Schema for updating a store"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[StoreAddress] = Field(None)
    coordinates: Optional[List[float]] = Field(None, description="[longitude, latitude]")
    contact: Optional[StoreContact] = Field(None)
    hours: Optional[StoreHoursCreate] = Field(None)
    services: Optional[List[str]] = Field(None)
    manager_id: Optional[str] = Field(None)
    capacity: Optional[int] = Field(None)
    is_active: Optional[bool] = Field(None)


class StoreInventoryUpdate(BaseModel):
    """Schema for updating store inventory"""
    product_id: str = Field(..., description="Product ID")
    variant_id: str = Field(..., description="Variant ID")
    quantity: int = Field(..., ge=0, description="New quantity")


class StoreSearchQuery(BaseModel):
    """Schema for store search query"""
    latitude: float = Field(..., ge=-90, le=90, description="Search center latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Search center longitude")
    radius: int = Field(default=10000, ge=1, le=100000, description="Search radius in meters")
    product_id: Optional[str] = Field(None, description="Filter stores with specific product")
    variant_id: Optional[str] = Field(None, description="Filter stores with specific variant")
    services: Optional[List[str]] = Field(None, description="Filter by available services")
    open_now: Optional[bool] = Field(None, description="Filter by stores open now")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")


class StoreResponse(BaseModel):
    """Schema for store response"""
    id: str = Field(..., description="Store ID")
    store_id: str = Field(..., description="Store identifier")
    name: str = Field(..., description="Store name")
    address: StoreAddress = Field(..., description="Store address")
    location: Location = Field(..., description="Store coordinates")
    contact: StoreContact = Field(..., description="Contact information")
    hours: Dict[str, StoreHours] = Field(..., description="Operating hours")
    services: List[str] = Field(..., description="Available services")
    manager_id: Optional[str] = Field(None, description="Store manager ID")
    capacity: Optional[int] = Field(None, description="Store capacity")
    is_active: bool = Field(..., description="Store status")
    is_open_now: bool = Field(..., description="Whether store is currently open")
    distance: Optional[float] = Field(None, description="Distance from search point in meters")
    available_products: Optional[List[str]] = Field(None, description="Available product IDs")
    created_at: datetime = Field(..., description="Creation date")


class StoreListResponse(BaseModel):
    """Schema for store list response"""
    stores: List[StoreResponse] = Field(..., description="List of stores")
    total: int = Field(..., description="Total number of stores found")
    search_center: Optional[Dict[str, float]] = Field(None, description="Search center coordinates")
    search_radius: Optional[int] = Field(None, description="Search radius in meters")


class StoreInventoryResponse(BaseModel):
    """Schema for store inventory response"""
    store_id: str = Field(..., description="Store ID")
    store_name: str = Field(..., description="Store name")
    inventory: List[StoreInventoryItem] = Field(..., description="Store inventory")
    total_items: int = Field(..., description="Total number of inventory items")


class NearbyStoreResponse(BaseModel):
    """Schema for nearby stores with specific product"""
    product_id: str = Field(..., description="Product ID")
    variant_id: Optional[str] = Field(None, description="Variant ID")
    stores: List[StoreResponse] = Field(..., description="Nearby stores with the product")
    total_stores: int = Field(..., description="Total stores found")