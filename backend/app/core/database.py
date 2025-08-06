"""
Database connection and initialization
"""
import motor.motor_asyncio
from beanie import init_beanie
from app.core.config import settings


class Database:
    """Database connection manager"""
    client: motor.motor_asyncio.AsyncIOMotorClient = None
    database: motor.motor_asyncio.AsyncIOMotorDatabase = None


# Create database instance
db = Database()


async def connect_to_mongo():
    """Create database connection"""
    print("Connecting to MongoDB...")
    db.client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
    db.database = db.client[settings.MONGODB_DB_NAME]
    print("Connected to MongoDB!")


async def close_mongo_connection():
    """Close database connection"""
    print("Closing MongoDB connection...")
    db.client.close()
    print("MongoDB connection closed!")


async def init_database():
    """Initialize database with models"""
    from app.models.user import User
    from app.models.product import Product, Category
    from app.models.order import Order
    from app.models.review import Review
    from app.models.cart import Cart
    from app.models.store import Store
    
    # Initialize beanie with the Product document class and a database
    await init_beanie(
        database=db.database,
        document_models=[
            User,
            Product,
            Category,
            Order,
            Review,
            Cart,
            Store
        ]
    )
    
    # Create indexes
    await create_indexes()
    print("Database initialized!")


async def create_indexes():
    """Create database indexes for optimal performance"""
    
    # Products collection indexes
    await db.database.products.create_index([
        ("name", "text"),
        ("description", "text"),
        ("search_keywords", "text"),
        ("brand", "text")
    ], name="text_search_index")
    
    await db.database.products.create_index([
        ("categories", 1),
        ("status", 1)
    ], name="category_status_index")
    
    await db.database.products.create_index([
        ("variants.price", 1)
    ], name="price_index")
    
    await db.database.products.create_index([
        ("rating_summary.average_rating", -1)
    ], name="rating_index")
    
    await db.database.products.create_index([
        ("variants.sku", 1)
    ], unique=True, name="sku_unique_index")
    
    # Users collection indexes
    await db.database.users.create_index([
        ("email", 1)
    ], unique=True, name="email_unique_index")
    
    await db.database.users.create_index([
        ("addresses.location", "2dsphere")
    ], name="user_location_index")
    
    # Orders collection indexes
    await db.database.orders.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ], name="user_orders_index")
    
    await db.database.orders.create_index([
        ("order_number", 1)
    ], unique=True, name="order_number_unique_index")
    
    await db.database.orders.create_index([
        ("status", 1),
        ("created_at", -1)
    ], name="status_date_index")
    
    # Reviews collection indexes
    await db.database.reviews.create_index([
        ("product_id", 1),
        ("status", 1),
        ("created_at", -1)
    ], name="product_reviews_index")
    
    await db.database.reviews.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ], name="user_reviews_index")
    
    # Carts collection indexes
    await db.database.carts.create_index([
        ("user_id", 1)
    ], name="user_cart_index")
    
    await db.database.carts.create_index([
        ("session_id", 1)
    ], name="session_cart_index")
    
    await db.database.carts.create_index([
        ("expires_at", 1)
    ], expireAfterSeconds=0, name="cart_expiry_index")
    
    # Stores collection indexes
    await db.database.stores.create_index([
        ("location", "2dsphere")
    ], name="store_location_index")
    
    await db.database.stores.create_index([
        ("store_id", 1)
    ], unique=True, name="store_id_unique_index")
    
    print("Database indexes created!")