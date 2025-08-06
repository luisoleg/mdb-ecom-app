# MongoDB Schema Design for E-commerce Platform

## Collections Overview

1. **products** - Product catalog with variants and inventory
2. **categories** - Product categories with hierarchical structure
3. **users** - User profiles, authentication, and preferences
4. **orders** - Order management and tracking
5. **reviews** - Product reviews and ratings
6. **carts** - Shopping cart management
7. **stores** - Physical store locations (for geospatial features)

## Schema Designs

### 1. Products Collection

```json
{
  "_id": ObjectId("..."),
  "sku": "PROD-001-VAR-001",
  "name": "Wireless Bluetooth Headphones",
  "description": "High-quality wireless headphones with noise cancellation",
  "brand": "TechAudio",
  "categories": [
    ObjectId("category_electronics"),
    ObjectId("category_audio")
  ],
  "base_price": 199.99,
  "variants": [
    {
      "variant_id": "VAR-001",
      "name": "Black - Large",
      "sku": "PROD-001-VAR-001",
      "price": 199.99,
      "attributes": {
        "color": "Black",
        "size": "Large"
      },
      "inventory": {
        "quantity": 50,
        "reserved": 5,
        "warehouse_location": "A1-B2-C3"
      },
      "images": [
        {
          "url": "https://cdn.example.com/products/headphones-black-1.jpg",
          "alt": "Black headphones front view",
          "is_primary": true
        }
      ]
    }
  ],
  "specifications": {
    "weight": "250g",
    "battery_life": "30 hours",
    "connectivity": ["Bluetooth 5.0", "USB-C"]
  },
  "seo": {
    "meta_title": "Wireless Bluetooth Headphones - TechAudio",
    "meta_description": "Premium wireless headphones with 30-hour battery life",
    "keywords": ["wireless", "bluetooth", "headphones", "noise cancellation"]
  },
  "search_keywords": ["headphones", "wireless", "bluetooth", "audio", "music"],
  "rating_summary": {
    "average_rating": 4.5,
    "total_reviews": 125,
    "rating_distribution": {
      "5": 75,
      "4": 30,
      "3": 15,
      "2": 3,
      "1": 2
    }
  },
  "status": "active",
  "created_at": ISODate("2024-01-01T00:00:00Z"),
  "updated_at": ISODate("2024-01-15T10:30:00Z"),
  "created_by": ObjectId("user_admin"),
  "tags": ["featured", "best-seller"]
}
```

### 2. Categories Collection

```json
{
  "_id": ObjectId("category_electronics"),
  "name": "Electronics",
  "slug": "electronics",
  "description": "Electronic devices and gadgets",
  "parent_id": null,
  "level": 0,
  "path": "/electronics",
  "children": [
    ObjectId("category_audio"),
    ObjectId("category_smartphones")
  ],
  "image": {
    "url": "https://cdn.example.com/categories/electronics.jpg",
    "alt": "Electronics category"
  },
  "seo": {
    "meta_title": "Electronics - Shop Latest Gadgets",
    "meta_description": "Browse our wide range of electronic devices"
  },
  "sort_order": 1,
  "is_active": true,
  "created_at": ISODate("2024-01-01T00:00:00Z")
}
```

### 3. Users Collection

```json
{
  "_id": ObjectId("..."),
  "email": "user@example.com",
  "password_hash": "$2b$12$...",
  "profile": {
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "date_of_birth": ISODate("1990-01-01T00:00:00Z"),
    "avatar": "https://cdn.example.com/avatars/user123.jpg"
  },
  "addresses": [
    {
      "address_id": "addr_001",
      "type": "shipping",
      "is_default": true,
      "recipient_name": "John Doe",
      "street": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "US",
      "location": {
        "type": "Point",
        "coordinates": [-73.935242, 40.730610]
      }
    }
  ],
  "payment_methods": [
    {
      "method_id": "pm_001",
      "type": "credit_card",
      "is_default": true,
      "last_four": "1234",
      "brand": "visa",
      "expires_at": "12/25",
      "stripe_payment_method_id": "pm_stripe_123"
    }
  ],
  "preferences": {
    "currency": "USD",
    "language": "en",
    "notifications": {
      "email_marketing": true,
      "order_updates": true,
      "push_notifications": false
    }
  },
  "wishlists": [
    {
      "name": "My Wishlist",
      "items": [
        {
          "product_id": ObjectId("..."),
          "variant_id": "VAR-001",
          "added_at": ISODate("2024-01-10T00:00:00Z")
        }
      ]
    }
  ],
  "loyalty": {
    "points": 1250,
    "tier": "gold",
    "lifetime_spent": 2500.00
  },
  "auth": {
    "is_verified": true,
    "verification_token": null,
    "reset_token": null,
    "last_login": ISODate("2024-01-15T10:30:00Z"),
    "login_count": 45
  },
  "status": "active",
  "created_at": ISODate("2024-01-01T00:00:00Z"),
  "updated_at": ISODate("2024-01-15T10:30:00Z")
}
```

### 4. Orders Collection

```json
{
  "_id": ObjectId("..."),
  "order_number": "ORD-2024-001001",
  "user_id": ObjectId("..."),
  "status": "processing",
  "items": [
    {
      "product_id": ObjectId("..."),
      "variant_id": "VAR-001",
      "sku": "PROD-001-VAR-001",
      "name": "Wireless Bluetooth Headphones - Black Large",
      "price": 199.99,
      "quantity": 2,
      "total": 399.98
    }
  ],
  "summary": {
    "subtotal": 399.98,
    "tax": 32.00,
    "shipping": 9.99,
    "discount": 20.00,
    "total": 421.97
  },
  "shipping_address": {
    "recipient_name": "John Doe",
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "US",
    "location": {
      "type": "Point",
      "coordinates": [-73.935242, 40.730610]
    }
  },
  "billing_address": {
    "recipient_name": "John Doe",
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "US"
  },
  "payment": {
    "method": "credit_card",
    "status": "completed",
    "transaction_id": "txn_stripe_123",
    "amount": 421.97,
    "currency": "USD",
    "processed_at": ISODate("2024-01-15T10:30:00Z")
  },
  "shipping": {
    "method": "standard",
    "carrier": "UPS",
    "tracking_number": "1Z123456789",
    "estimated_delivery": ISODate("2024-01-20T00:00:00Z")
  },
  "timeline": [
    {
      "status": "pending",
      "timestamp": ISODate("2024-01-15T10:30:00Z"),
      "note": "Order placed"
    },
    {
      "status": "processing",
      "timestamp": ISODate("2024-01-15T11:00:00Z"),
      "note": "Payment confirmed, preparing for shipment"
    }
  ],
  "notes": "Please leave at front door",
  "created_at": ISODate("2024-01-15T10:30:00Z"),
  "updated_at": ISODate("2024-01-15T11:00:00Z")
}
```

### 5. Reviews Collection

```json
{
  "_id": ObjectId("..."),
  "product_id": ObjectId("..."),
  "variant_id": "VAR-001",
  "user_id": ObjectId("..."),
  "order_id": ObjectId("..."),
  "rating": 5,
  "title": "Excellent sound quality!",
  "content": "These headphones exceeded my expectations. The noise cancellation is amazing and the battery life is exactly as advertised.",
  "pros": ["Great sound quality", "Long battery life", "Comfortable fit"],
  "cons": ["Slightly heavy"],
  "verified_purchase": true,
  "helpful_votes": 15,
  "total_votes": 18,
  "images": [
    {
      "url": "https://cdn.example.com/reviews/rev123_img1.jpg",
      "alt": "Headphones in use"
    }
  ],
  "status": "approved",
  "created_at": ISODate("2024-01-20T00:00:00Z"),
  "updated_at": ISODate("2024-01-20T00:00:00Z")
}
```

### 6. Carts Collection

```json
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "session_id": "sess_anonymous_123",
  "items": [
    {
      "product_id": ObjectId("..."),
      "variant_id": "VAR-001",
      "quantity": 2,
      "price": 199.99,
      "added_at": ISODate("2024-01-15T10:00:00Z")
    }
  ],
  "totals": {
    "items_count": 2,
    "subtotal": 399.98,
    "estimated_tax": 32.00,
    "estimated_shipping": 9.99,
    "estimated_total": 441.97
  },
  "expires_at": ISODate("2024-01-22T10:00:00Z"),
  "created_at": ISODate("2024-01-15T10:00:00Z"),
  "updated_at": ISODate("2024-01-15T10:30:00Z")
}
```

### 7. Stores Collection (for Geospatial Features)

```json
{
  "_id": ObjectId("..."),
  "store_id": "STORE-NYC-001",
  "name": "TechMart Manhattan",
  "address": {
    "street": "456 Broadway",
    "city": "New York",
    "state": "NY",
    "postal_code": "10013",
    "country": "US"
  },
  "location": {
    "type": "Point",
    "coordinates": [-74.0059, 40.7128]
  },
  "contact": {
    "phone": "+1234567890",
    "email": "manhattan@techmart.com"
  },
  "hours": {
    "monday": {"open": "09:00", "close": "21:00"},
    "tuesday": {"open": "09:00", "close": "21:00"},
    "wednesday": {"open": "09:00", "close": "21:00"},
    "thursday": {"open": "09:00", "close": "21:00"},
    "friday": {"open": "09:00", "close": "22:00"},
    "saturday": {"open": "10:00", "close": "22:00"},
    "sunday": {"open": "11:00", "close": "20:00"}
  },
  "services": ["pickup", "returns", "tech_support"],
  "inventory": [
    {
      "product_id": ObjectId("..."),
      "variant_id": "VAR-001",
      "quantity": 15
    }
  ],
  "is_active": true,
  "created_at": ISODate("2024-01-01T00:00:00Z")
}
```

## Indexing Strategy

### Products Collection Indexes
```javascript
// Text search index
db.products.createIndex({
  "name": "text",
  "description": "text",
  "search_keywords": "text",
  "brand": "text"
})

// Category and status filtering
db.products.createIndex({"categories": 1, "status": 1})

// Price range filtering
db.products.createIndex({"variants.price": 1})

// Rating filtering
db.products.createIndex({"rating_summary.average_rating": -1})

// SKU unique index
db.products.createIndex({"variants.sku": 1}, {unique: true})
```

### Users Collection Indexes
```javascript
// Email unique index
db.users.createIndex({"email": 1}, {unique: true})

// Geospatial index for addresses
db.users.createIndex({"addresses.location": "2dsphere"})
```

### Orders Collection Indexes
```javascript
// User orders
db.orders.createIndex({"user_id": 1, "created_at": -1})

// Order number unique index
db.orders.createIndex({"order_number": 1}, {unique: true})

// Status and date filtering
db.orders.createIndex({"status": 1, "created_at": -1})
```

### Stores Collection Indexes
```javascript
// Geospatial index for store locations
db.stores.createIndex({"location": "2dsphere"})
```