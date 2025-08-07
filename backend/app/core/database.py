"""
Database connection and initialization
"""
import motor.motor_asyncio
from beanie import init_beanie

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Database:
    """Database connection manager"""

    client: motor.motor_asyncio.AsyncIOMotorClient = None
    database: motor.motor_asyncio.AsyncIOMotorDatabase = None


# Create database instance
db = Database()


async def connect_to_mongo():
    """Create database connection"""
    logger.info(
        "Connecting to MongoDB",
        url=settings.MONGODB_URL,
        database=settings.MONGODB_DB_NAME,
    )
    db.client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
    db.database = db.client[settings.MONGODB_DB_NAME]
    logger.info("Connected to MongoDB successfully")


async def close_mongo_connection():
    """Close database connection"""
    logger.info("Closing MongoDB connection")
    db.client.close()
    logger.info("MongoDB connection closed successfully")


async def init_database():
    """Initialize database with models"""
    from app.models.cart import Cart
    from app.models.order import Order
    from app.models.product import Category, Product
    from app.models.review import Review
    from app.models.store import Store
    from app.models.user import User

    # Initialize beanie with the Product document class and a database
    # Disable automatic index creation to avoid conflicts
    await init_beanie(
        database=db.database,
        document_models=[User, Product, Category, Order, Review, Cart, Store],
        allow_index_dropping=True,  # Allow Beanie to drop indexes if needed
    )

    # Create indexes
    await create_indexes()
    logger.info("Database initialized successfully")


async def create_indexes():
    """Create database indexes for optimal performance"""

    logger.info("Starting database index cleanup and recreation")

    # Nuclear approach: Drop collections entirely to clear all indexes
    # This is safe since we're in development and will recreate the indexes
    collections_to_clean = [
        "products",
        "users",
        "orders",
        "reviews",
        "carts",
        "stores",
    ]

    for collection_name in collections_to_clean:
        try:
            collection = db.database[collection_name]

            # Check if collection exists and has documents
            try:
                doc_count = await collection.count_documents({})
                logger.debug(
                    "Collection document count",
                    collection=collection_name,
                    document_count=doc_count,
                )

                # Drop the entire collection (this removes all indexes and data)
                await collection.drop()
                logger.debug(
                    "Dropped collection for index cleanup",
                    collection=collection_name,
                )

            except Exception as e:
                logger.warning(
                    "Could not drop collection",
                    collection=collection_name,
                    error=str(e),
                )

        except Exception as e:
            logger.error(
                "Error processing collection",
                collection=collection_name,
                error=str(e),
            )

    logger.info("Database cleanup completed, recreating indexes")

    # Products collection indexes
    indexes_to_create = [
        {
            "collection": "products",
            "fields": [
                ("name", "text"),
                ("description", "text"),
                ("search_keywords", "text"),
                ("brand", "text"),
            ],
            "name": "text_search_index",
            "options": {},
        },
        {
            "collection": "products",
            "fields": [("categories", 1), ("status", 1)],
            "name": "category_status_index",
            "options": {},
        },
        {
            "collection": "products",
            "fields": [("variants.price", 1)],
            "name": "price_index",
            "options": {},
        },
        {
            "collection": "products",
            "fields": [("rating_summary.average_rating", -1)],
            "name": "rating_index",
            "options": {},
        },
        {
            "collection": "products",
            "fields": [("variants.sku", 1)],
            "name": "sku_unique_index",
            "options": {"unique": True},
        },
        # Users collection indexes
        {
            "collection": "users",
            "fields": [("email", 1)],
            "name": "email_unique_index",
            "options": {"unique": True},
        },
        {
            "collection": "users",
            "fields": [("addresses.location", "2dsphere")],
            "name": "user_location_index",
            "options": {},
        },
        # Orders collection indexes
        {
            "collection": "orders",
            "fields": [("user_id", 1), ("created_at", -1)],
            "name": "user_orders_index",
            "options": {},
        },
        {
            "collection": "orders",
            "fields": [("order_number", 1)],
            "name": "order_number_unique_index",
            "options": {"unique": True},
        },
        {
            "collection": "orders",
            "fields": [("status", 1), ("created_at", -1)],
            "name": "status_date_index",
            "options": {},
        },
        # Reviews collection indexes
        {
            "collection": "reviews",
            "fields": [("product_id", 1), ("status", 1), ("created_at", -1)],
            "name": "product_reviews_index",
            "options": {},
        },
        {
            "collection": "reviews",
            "fields": [("user_id", 1), ("created_at", -1)],
            "name": "user_reviews_index",
            "options": {},
        },
        # Carts collection indexes
        {
            "collection": "carts",
            "fields": [("user_id", 1)],
            "name": "user_cart_index",
            "options": {},
        },
        {
            "collection": "carts",
            "fields": [("session_id", 1)],
            "name": "session_cart_index",
            "options": {},
        },
        {
            "collection": "carts",
            "fields": [("expires_at", 1)],
            "name": "cart_expiry_index",
            "options": {"expireAfterSeconds": 0},
        },
        # Stores collection indexes
        {
            "collection": "stores",
            "fields": [("location", "2dsphere")],
            "name": "store_location_index",
            "options": {},
        },
        {
            "collection": "stores",
            "fields": [("store_id", 1)],
            "name": "store_id_unique_index",
            "options": {"unique": True},
        },
    ]

    # Create all indexes with intelligent conflict detection
    created_count = 0
    skipped_count = 0
    failed_count = 0

    for index_config in indexes_to_create:
        collection_name = index_config["collection"]
        fields = index_config["fields"]
        index_name = index_config["name"]
        options = index_config["options"]

        try:
            collection = db.database[collection_name]

            # Check if index already exists
            existing_indexes = await collection.list_indexes().to_list(
                length=None
            )
            existing_names = [idx.get("name", "") for idx in existing_indexes]

            if index_name in existing_names:
                logger.debug(
                    "Index already exists, skipping",
                    index_name=index_name,
                    collection=collection_name,
                )
                skipped_count += 1
                continue

            # Check if same fields exist with different name
            field_signatures = []
            for idx in existing_indexes:
                if idx.get("name", "") != "_id_":
                    key_spec = idx.get("key", {})
                    signature = tuple(sorted(key_spec.items()))
                    field_signatures.append(signature)

            new_signature = tuple(
                sorted([(field, direction) for field, direction in fields])
            )
            if new_signature in field_signatures:
                logger.debug(
                    "Index with same fields already exists, skipping",
                    index_name=index_name,
                    collection=collection_name,
                )
                skipped_count += 1
                continue

            # Try to create the index
            await collection.create_index(fields, name=index_name, **options)
            logger.debug(
                "Created index",
                index_name=index_name,
                collection=collection_name,
            )
            created_count += 1

        except Exception as e:
            error_msg = str(e)
            if (
                "already exists" in error_msg.lower()
                or "indexoptionsconflict" in error_msg.lower()
            ):
                logger.debug(
                    "Index conflict, skipping",
                    index_name=index_name,
                    collection=collection_name,
                )
                skipped_count += 1
            else:
                logger.error(
                    "Failed to create index",
                    index_name=index_name,
                    collection=collection_name,
                    error=error_msg[:150],
                )
                failed_count += 1

    logger.info(
        "Index creation completed",
        created=created_count,
        skipped=skipped_count,
        failed=failed_count,
    )
