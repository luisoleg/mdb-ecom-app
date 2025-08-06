// MongoDB Queries for E-commerce Platform
// This file contains example queries for key operations

// ================================
// 1. PRODUCT SEARCH AND FILTERING
// ================================

// Full-text search with category and price filtering
db.products.find({
  $and: [
    { $text: { $search: "wireless headphones" } },
    { categories: ObjectId("category_audio") },
    { "variants.price": { $gte: 100, $lte: 300 } },
    { status: "active" }
  ]
}).sort({ score: { $meta: "textScore" }, "rating_summary.average_rating": -1 })

// Advanced product filtering with aggregation
db.products.aggregate([
  {
    $match: {
      status: "active",
      "variants.price": { $gte: 50, $lte: 500 }
    }
  },
  {
    $lookup: {
      from: "categories",
      localField: "categories",
      foreignField: "_id",
      as: "category_info"
    }
  },
  {
    $addFields: {
      min_price: { $min: "$variants.price" },
      max_price: { $max: "$variants.price" },
      total_inventory: { $sum: "$variants.inventory.quantity" }
    }
  },
  {
    $match: {
      total_inventory: { $gt: 0 },
      "rating_summary.average_rating": { $gte: 4.0 }
    }
  },
  {
    $sort: { "rating_summary.average_rating": -1, created_at: -1 }
  },
  {
    $limit: 20
  }
])

// Search products by brand and specifications
db.products.find({
  brand: "TechAudio",
  "specifications.connectivity": { $in: ["Bluetooth 5.0"] },
  "variants.inventory.quantity": { $gt: 0 }
})

// ================================
// 2. INVENTORY MANAGEMENT
// ================================

// Update inventory after purchase (decrease stock)
db.products.updateOne(
  { 
    "_id": ObjectId("product_id"),
    "variants.variant_id": "VAR-001",
    "variants.inventory.quantity": { $gte: 2 }
  },
  { 
    $inc: { 
      "variants.$.inventory.quantity": -2,
      "variants.$.inventory.reserved": -2
    }
  }
)

// Reserve inventory for cart items
db.products.updateOne(
  { 
    "_id": ObjectId("product_id"),
    "variants.variant_id": "VAR-001"
  },
  { 
    $inc: { "variants.$.inventory.reserved": 2 }
  }
)

// Check low stock products
db.products.find({
  "variants.inventory.quantity": { $lt: 10 },
  status: "active"
}).sort({ "variants.inventory.quantity": 1 })

// Bulk inventory update
db.products.bulkWrite([
  {
    updateOne: {
      filter: { "_id": ObjectId("product1"), "variants.variant_id": "VAR-001" },
      update: { $inc: { "variants.$.inventory.quantity": -1 } }
    }
  },
  {
    updateOne: {
      filter: { "_id": ObjectId("product2"), "variants.variant_id": "VAR-002" },
      update: { $inc: { "variants.$.inventory.quantity": -3 } }
    }
  }
])

// ================================
// 3. ANALYTICS QUERIES
// ================================

// Most sold products (by quantity)
db.orders.aggregate([
  {
    $match: {
      status: { $in: ["completed", "shipped", "delivered"] },
      created_at: { 
        $gte: ISODate("2024-01-01T00:00:00Z"),
        $lte: ISODate("2024-12-31T23:59:59Z")
      }
    }
  },
  { $unwind: "$items" },
  {
    $group: {
      _id: "$items.product_id",
      total_quantity: { $sum: "$items.quantity" },
      total_revenue: { $sum: "$items.total" },
      orders_count: { $sum: 1 },
      product_name: { $first: "$items.name" }
    }
  },
  { $sort: { total_quantity: -1 } },
  { $limit: 10 }
])

// Revenue by category
db.orders.aggregate([
  {
    $match: {
      status: { $in: ["completed", "shipped", "delivered"] },
      created_at: { 
        $gte: ISODate("2024-01-01T00:00:00Z"),
        $lte: ISODate("2024-12-31T23:59:59Z")
      }
    }
  },
  { $unwind: "$items" },
  {
    $lookup: {
      from: "products",
      localField: "items.product_id",
      foreignField: "_id",
      as: "product"
    }
  },
  { $unwind: "$product" },
  { $unwind: "$product.categories" },
  {
    $lookup: {
      from: "categories",
      localField: "product.categories",
      foreignField: "_id",
      as: "category"
    }
  },
  { $unwind: "$category" },
  {
    $group: {
      _id: "$category._id",
      category_name: { $first: "$category.name" },
      total_revenue: { $sum: "$items.total" },
      orders_count: { $sum: 1 },
      products_sold: { $sum: "$items.quantity" }
    }
  },
  { $sort: { total_revenue: -1 } }
])

// Customer Lifetime Value (CLV)
db.orders.aggregate([
  {
    $match: {
      status: { $in: ["completed", "shipped", "delivered"] }
    }
  },
  {
    $group: {
      _id: "$user_id",
      total_orders: { $sum: 1 },
      total_spent: { $sum: "$summary.total" },
      first_order: { $min: "$created_at" },
      last_order: { $max: "$created_at" },
      avg_order_value: { $avg: "$summary.total" }
    }
  },
  {
    $addFields: {
      customer_lifespan_days: {
        $divide: [
          { $subtract: ["$last_order", "$first_order"] },
          1000 * 60 * 60 * 24
        ]
      }
    }
  },
  {
    $match: {
      total_spent: { $gte: 100 }
    }
  },
  { $sort: { total_spent: -1 } }
])

// Monthly revenue trends
db.orders.aggregate([
  {
    $match: {
      status: { $in: ["completed", "shipped", "delivered"] },
      created_at: { $gte: ISODate("2024-01-01T00:00:00Z") }
    }
  },
  {
    $group: {
      _id: {
        year: { $year: "$created_at" },
        month: { $month: "$created_at" }
      },
      revenue: { $sum: "$summary.total" },
      orders_count: { $sum: 1 },
      avg_order_value: { $avg: "$summary.total" }
    }
  },
  { $sort: { "_id.year": 1, "_id.month": 1 } }
])

// ================================
// 4. USER BEHAVIOR ANALYTICS
// ================================

// Cart abandonment analysis
db.carts.aggregate([
  {
    $match: {
      created_at: { $gte: ISODate("2024-01-01T00:00:00Z") }
    }
  },
  {
    $lookup: {
      from: "orders",
      let: { user_id: "$user_id", cart_created: "$created_at" },
      pipeline: [
        {
          $match: {
            $expr: {
              $and: [
                { $eq: ["$user_id", "$$user_id"] },
                { $gte: ["$created_at", "$$cart_created"] }
              ]
            }
          }
        }
      ],
      as: "orders"
    }
  },
  {
    $addFields: {
      was_converted: { $gt: [{ $size: "$orders" }, 0] }
    }
  },
  {
    $group: {
      _id: null,
      total_carts: { $sum: 1 },
      converted_carts: { $sum: { $cond: ["$was_converted", 1, 0] } },
      abandonment_rate: {
        $avg: { $cond: ["$was_converted", 0, 1] }
      }
    }
  }
])

// ================================
// 5. GEOSPATIAL QUERIES
// ================================

// Find stores near user location (within 10km)
db.stores.find({
  location: {
    $near: {
      $geometry: {
        type: "Point",
        coordinates: [-73.935242, 40.730610] // user location
      },
      $maxDistance: 10000 // 10km in meters
    }
  },
  is_active: true
})

// Find stores with specific product in stock within radius
db.stores.aggregate([
  {
    $geoNear: {
      near: {
        type: "Point",
        coordinates: [-73.935242, 40.730610]
      },
      distanceField: "distance",
      maxDistance: 50000, // 50km
      spherical: true
    }
  },
  {
    $match: {
      is_active: true,
      "inventory.product_id": ObjectId("product_id"),
      "inventory.quantity": { $gt: 0 }
    }
  },
  {
    $project: {
      name: 1,
      address: 1,
      contact: 1,
      distance: 1,
      available_quantity: {
        $arrayElemAt: [
          {
            $filter: {
              input: "$inventory",
              cond: { $eq: ["$$this.product_id", ObjectId("product_id")] }
            }
          },
          0
        ]
      }
    }
  },
  { $sort: { distance: 1 } }
])

// ================================
// 6. REVIEW AND RATING QUERIES
// ================================

// Calculate and update product rating summary
db.reviews.aggregate([
  {
    $match: {
      product_id: ObjectId("product_id"),
      status: "approved"
    }
  },
  {
    $group: {
      _id: "$product_id",
      average_rating: { $avg: "$rating" },
      total_reviews: { $sum: 1 },
      rating_distribution: {
        $push: "$rating"
      }
    }
  },
  {
    $addFields: {
      rating_counts: {
        "5": {
          $size: {
            $filter: {
              input: "$rating_distribution",
              cond: { $eq: ["$$this", 5] }
            }
          }
        },
        "4": {
          $size: {
            $filter: {
              input: "$rating_distribution",
              cond: { $eq: ["$$this", 4] }
            }
          }
        },
        "3": {
          $size: {
            $filter: {
              input: "$rating_distribution",
              cond: { $eq: ["$$this", 3] }
            }
          }
        },
        "2": {
          $size: {
            $filter: {
              input: "$rating_distribution",
              cond: { $eq: ["$$this", 2] }
            }
          }
        },
        "1": {
          $size: {
            $filter: {
              input: "$rating_distribution",
              cond: { $eq: ["$$this", 1] }
            }
          }
        }
      }
    }
  }
])

// Get helpful reviews for a product
db.reviews.find({
  product_id: ObjectId("product_id"),
  status: "approved",
  helpful_votes: { $gte: 5 }
}).sort({ helpful_votes: -1, created_at: -1 }).limit(10)

// ================================
// 7. SEARCH AND RECOMMENDATION QUERIES
// ================================

// Products frequently bought together
db.orders.aggregate([
  { $unwind: "$items" },
  {
    $lookup: {
      from: "orders",
      let: { order_id: "$_id", product_id: "$items.product_id" },
      pipeline: [
        { $match: { $expr: { $eq: ["$_id", "$$order_id"] } } },
        { $unwind: "$items" },
        { $match: { $expr: { $ne: ["$items.product_id", "$$product_id"] } } }
      ],
      as: "other_items"
    }
  },
  { $unwind: "$other_items" },
  {
    $group: {
      _id: {
        product_a: "$items.product_id",
        product_b: "$other_items.items.product_id"
      },
      frequency: { $sum: 1 }
    }
  },
  {
    $match: {
      "_id.product_a": ObjectId("target_product_id")
    }
  },
  { $sort: { frequency: -1 } },
  { $limit: 5 }
])

// Personalized product recommendations based on user's order history
db.orders.aggregate([
  {
    $match: {
      user_id: ObjectId("user_id"),
      status: { $in: ["completed", "shipped", "delivered"] }
    }
  },
  { $unwind: "$items" },
  {
    $lookup: {
      from: "products",
      localField: "items.product_id",
      foreignField: "_id",
      as: "product"
    }
  },
  { $unwind: "$product" },
  { $unwind: "$product.categories" },
  {
    $group: {
      _id: "$product.categories",
      purchase_count: { $sum: "$items.quantity" }
    }
  },
  { $sort: { purchase_count: -1 } },
  { $limit: 3 },
  {
    $lookup: {
      from: "products",
      let: { category_id: "$_id" },
      pipeline: [
        {
          $match: {
            $expr: { $in: ["$$category_id", "$categories"] },
            status: "active",
            "rating_summary.average_rating": { $gte: 4.0 }
          }
        },
        { $sample: { size: 5 } }
      ],
      as: "recommended_products"
    }
  }
])