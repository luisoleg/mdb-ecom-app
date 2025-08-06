"""
Analytics endpoints for business intelligence
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.security import get_current_user_id
from app.models.order import Order
from app.models.product import Product, Category
from app.models.user import User
from app.models.review import Review

router = APIRouter()


class SalesMetrics(BaseModel):
    """Sales metrics response model"""
    total_revenue: float
    total_orders: int
    average_order_value: float
    total_customers: int


class ProductSalesData(BaseModel):
    """Product sales data model"""
    product_id: str
    product_name: str
    total_quantity: int
    total_revenue: float
    orders_count: int


class CategorySalesData(BaseModel):
    """Category sales data model"""
    category_id: str
    category_name: str
    total_revenue: float
    orders_count: int
    products_sold: int


class CustomerLifetimeValue(BaseModel):
    """Customer lifetime value model"""
    user_id: str
    total_orders: int
    total_spent: float
    avg_order_value: float
    first_order_date: datetime
    last_order_date: datetime
    customer_lifespan_days: int


class RevenueByPeriod(BaseModel):
    """Revenue by time period model"""
    period: str  # YYYY-MM format
    revenue: float
    orders_count: int
    avg_order_value: float


class InventoryAlert(BaseModel):
    """Low inventory alert model"""
    product_id: str
    product_name: str
    variant_id: str
    variant_name: str
    current_stock: int
    threshold: int


@router.get("/sales-metrics", response_model=SalesMetrics)
async def get_sales_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Get overall sales metrics"""
    
    # Set default date range (last 30 days if not specified)
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Aggregation pipeline for sales metrics
    pipeline = [
        {
            "$match": {
                "status": {"$in": ["completed", "shipped", "delivered"]},
                "created_at": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$summary.total"},
                "total_orders": {"$sum": 1},
                "unique_customers": {"$addToSet": "$user_id"}
            }
        },
        {
            "$addFields": {
                "total_customers": {"$size": "$unique_customers"},
                "average_order_value": {
                    "$cond": {
                        "if": {"$gt": ["$total_orders", 0]},
                        "then": {"$divide": ["$total_revenue", "$total_orders"]},
                        "else": 0
                    }
                }
            }
        }
    ]
    
    result = await Order.aggregate(pipeline).to_list()
    
    if result:
        data = result[0]
        return SalesMetrics(
            total_revenue=round(data.get("total_revenue", 0), 2),
            total_orders=data.get("total_orders", 0),
            average_order_value=round(data.get("average_order_value", 0), 2),
            total_customers=data.get("total_customers", 0)
        )
    else:
        return SalesMetrics(
            total_revenue=0.0,
            total_orders=0,
            average_order_value=0.0,
            total_customers=0
        )


@router.get("/top-products", response_model=List[ProductSalesData])
async def get_top_selling_products(
    limit: int = Query(10, ge=1, le=50, description="Number of top products to return"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Get top-selling products by quantity"""
    
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    pipeline = [
        {
            "$match": {
                "status": {"$in": ["completed", "shipped", "delivered"]},
                "created_at": {"$gte": start_date, "$lte": end_date}
            }
        },
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.product_id",
                "total_quantity": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": "$items.total"},
                "orders_count": {"$sum": 1},
                "product_name": {"$first": "$items.name"}
            }
        },
        {"$sort": {"total_quantity": -1}},
        {"$limit": limit}
    ]
    
    results = await Order.aggregate(pipeline).to_list()
    
    return [
        ProductSalesData(
            product_id=str(item["_id"]),
            product_name=item["product_name"],
            total_quantity=item["total_quantity"],
            total_revenue=round(item["total_revenue"], 2),
            orders_count=item["orders_count"]
        ) for item in results
    ]


@router.get("/revenue-by-category", response_model=List[CategorySalesData])
async def get_revenue_by_category(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Get revenue breakdown by product category"""
    
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    pipeline = [
        {
            "$match": {
                "status": {"$in": ["completed", "shipped", "delivered"]},
                "created_at": {"$gte": start_date, "$lte": end_date}
            }
        },
        {"$unwind": "$items"},
        {
            "$lookup": {
                "from": "products",
                "localField": "items.product_id",
                "foreignField": "_id",
                "as": "product"
            }
        },
        {"$unwind": "$product"},
        {"$unwind": "$product.categories"},
        {
            "$lookup": {
                "from": "categories",
                "localField": "product.categories",
                "foreignField": "_id",
                "as": "category"
            }
        },
        {"$unwind": "$category"},
        {
            "$group": {
                "_id": "$category._id",
                "category_name": {"$first": "$category.name"},
                "total_revenue": {"$sum": "$items.total"},
                "orders_count": {"$sum": 1},
                "products_sold": {"$sum": "$items.quantity"}
            }
        },
        {"$sort": {"total_revenue": -1}}
    ]
    
    results = await Order.aggregate(pipeline).to_list()
    
    return [
        CategorySalesData(
            category_id=str(item["_id"]),
            category_name=item["category_name"],
            total_revenue=round(item["total_revenue"], 2),
            orders_count=item["orders_count"],
            products_sold=item["products_sold"]
        ) for item in results
    ]


@router.get("/customer-lifetime-value", response_model=List[CustomerLifetimeValue])
async def get_customer_lifetime_value(
    limit: int = Query(50, ge=1, le=100),
    min_orders: int = Query(2, ge=1, description="Minimum number of orders"),
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Get customer lifetime value analysis"""
    
    pipeline = [
        {
            "$match": {
                "status": {"$in": ["completed", "shipped", "delivered"]}
            }
        },
        {
            "$group": {
                "_id": "$user_id",
                "total_orders": {"$sum": 1},
                "total_spent": {"$sum": "$summary.total"},
                "first_order": {"$min": "$created_at"},
                "last_order": {"$max": "$created_at"},
                "avg_order_value": {"$avg": "$summary.total"}
            }
        },
        {
            "$addFields": {
                "customer_lifespan_days": {
                    "$divide": [
                        {"$subtract": ["$last_order", "$first_order"]},
                        1000 * 60 * 60 * 24
                    ]
                }
            }
        },
        {
            "$match": {
                "total_orders": {"$gte": min_orders}
            }
        },
        {"$sort": {"total_spent": -1}},
        {"$limit": limit}
    ]
    
    results = await Order.aggregate(pipeline).to_list()
    
    return [
        CustomerLifetimeValue(
            user_id=str(item["_id"]),
            total_orders=item["total_orders"],
            total_spent=round(item["total_spent"], 2),
            avg_order_value=round(item["avg_order_value"], 2),
            first_order_date=item["first_order"],
            last_order_date=item["last_order"],
            customer_lifespan_days=int(item["customer_lifespan_days"])
        ) for item in results
    ]


@router.get("/revenue-trends", response_model=List[RevenueByPeriod])
async def get_revenue_trends(
    months: int = Query(12, ge=1, le=24, description="Number of months to analyze"),
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Get monthly revenue trends"""
    
    start_date = datetime.utcnow() - timedelta(days=months * 30)
    
    pipeline = [
        {
            "$match": {
                "status": {"$in": ["completed", "shipped", "delivered"]},
                "created_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"}
                },
                "revenue": {"$sum": "$summary.total"},
                "orders_count": {"$sum": 1},
                "avg_order_value": {"$avg": "$summary.total"}
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]
    
    results = await Order.aggregate(pipeline).to_list()
    
    return [
        RevenueByPeriod(
            period=f"{item['_id']['year']}-{item['_id']['month']:02d}",
            revenue=round(item["revenue"], 2),
            orders_count=item["orders_count"],
            avg_order_value=round(item["avg_order_value"], 2)
        ) for item in results
    ]


@router.get("/inventory-alerts", response_model=List[InventoryAlert])
async def get_inventory_alerts(
    threshold: int = Query(10, ge=1, description="Stock threshold for alerts"),
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Get low inventory alerts"""
    
    pipeline = [
        {
            "$match": {
                "status": "active",
                "variants.inventory.quantity": {"$lt": threshold}
            }
        },
        {"$unwind": "$variants"},
        {
            "$match": {
                "variants.inventory.quantity": {"$lt": threshold}
            }
        },
        {
            "$project": {
                "product_name": "$name",
                "variant_id": "$variants.variant_id",
                "variant_name": "$variants.name",
                "current_stock": "$variants.inventory.quantity"
            }
        },
        {"$sort": {"current_stock": 1}}
    ]
    
    results = await Product.aggregate(pipeline).to_list()
    
    return [
        InventoryAlert(
            product_id=str(item["_id"]),
            product_name=item["product_name"],
            variant_id=item["variant_id"],
            variant_name=item["variant_name"],
            current_stock=item["current_stock"],
            threshold=threshold
        ) for item in results
    ]


@router.get("/dashboard-summary")
async def get_dashboard_summary(
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """Get summary data for admin dashboard"""
    
    # Get basic counts
    total_products = await Product.find(Product.status == "active").count()
    total_users = await User.find(User.status == "active").count()
    total_orders = await Order.find().count()
    total_reviews = await Review.find(Review.status == "approved").count()
    
    # Get recent sales metrics (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_revenue = await Order.aggregate([
        {
            "$match": {
                "status": {"$in": ["completed", "shipped", "delivered"]},
                "created_at": {"$gte": thirty_days_ago}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$summary.total"},
                "total_orders": {"$sum": 1}
            }
        }
    ]).to_list()
    
    recent_stats = recent_revenue[0] if recent_revenue else {"total_revenue": 0, "total_orders": 0}
    
    # Get low stock count
    low_stock_count = await Product.aggregate([
        {
            "$match": {
                "status": "active",
                "variants.inventory.quantity": {"$lt": 10}
            }
        },
        {"$count": "low_stock_products"}
    ]).to_list()
    
    low_stock = low_stock_count[0]["low_stock_products"] if low_stock_count else 0
    
    return {
        "total_products": total_products,
        "total_users": total_users,
        "total_orders": total_orders,
        "total_reviews": total_reviews,
        "recent_revenue": round(recent_stats["total_revenue"], 2),
        "recent_orders": recent_stats["total_orders"],
        "low_stock_products": low_stock,
        "generated_at": datetime.utcnow()
    }