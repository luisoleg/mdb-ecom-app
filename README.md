# E-commerce Platform

A comprehensive, scalable e-commerce platform built with FastAPI (Python) backend, React (TypeScript) frontend, and MongoDB database. This platform demonstrates modern web development practices with full-text search, geospatial features, real-time analytics, and secure payment processing.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend │    │   MongoDB Atlas  │
│   (TypeScript)   │◄──►│     (Python)     │◄──►│    Database     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
    │ Netlify/│             │AWS ECS/ │             │ MongoDB │
    │ Vercel  │             │ Railway │             │ Indexes │
    └─────────┘             └─────────┘             └─────────┘
```

## 🚀 Features

### Core E-commerce Features
- ✅ **Product Management**: Complete CRUD operations with variants, inventory tracking
- ✅ **User Authentication**: JWT-based auth with password strength validation
- ✅ **Shopping Cart**: Session-based cart for anonymous users, persistent for authenticated users
- ✅ **Order Management**: Complete order lifecycle with status tracking
- ✅ **Review System**: Product reviews with helpfulness voting
- ✅ **Search & Filtering**: Full-text search with advanced filtering options

### Advanced Features
- ✅ **Geospatial Queries**: Store locator using MongoDB's geospatial capabilities
- ✅ **Analytics Dashboard**: Sales metrics, customer insights, inventory alerts
- ✅ **Real-time Inventory**: Stock management with reservation system
- ✅ **Recommendation Engine**: Product recommendations based on purchase history
- ✅ **Security Features**: JWT tokens, input validation, CORS protection

### Technical Features
- ✅ **Scalable Backend**: FastAPI with async/await, automatic API documentation
- ✅ **Modern Frontend**: React 18 with TypeScript, Redux Toolkit, Tailwind CSS
- ✅ **Database Optimization**: Comprehensive indexing strategy for performance
- ✅ **API Design**: RESTful APIs with proper HTTP status codes and error handling
- ✅ **Type Safety**: Full TypeScript coverage on frontend, Pydantic models on backend

## 📁 Project Structure

```
ecom-platform/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── core/           # Configuration, security, database
│   │   ├── models/         # Pydantic/Beanie models
│   │   └── services/       # Business logic
│   ├── main.py             # FastAPI application entry point
│   └── requirements.txt    # Python dependencies
├── frontend/               # React Frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API service layer
│   │   ├── store/          # Redux store and slices
│   │   └── hooks/          # Custom React hooks
│   ├── package.json        # Node.js dependencies
│   └── tailwind.config.js  # Tailwind CSS configuration
├── database/               # Database schemas and queries
└── docs/                   # Documentation
```

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Database**: MongoDB with Beanie ODM
- **Authentication**: JWT with python-jose
- **Security**: Passlib for password hashing, CORS middleware
- **Validation**: Pydantic v2 for data validation
- **Documentation**: Automatic OpenAPI/Swagger docs

### Frontend
- **Framework**: React 18 with TypeScript
- **State Management**: Redux Toolkit
- **Routing**: React Router v6
- **Styling**: Tailwind CSS
- **Forms**: Formik with Yup validation
- **HTTP Client**: Axios with interceptors

### Database
- **Primary**: MongoDB Atlas
- **ODM**: Beanie (async MongoDB ODM)
- **Features**: Full-text search, geospatial queries, aggregation pipelines
- **Indexing**: Comprehensive indexing strategy for performance

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+
- MongoDB Atlas account (or local MongoDB)
- Git

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ecom-platform/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**
   ```bash
   cp env.example .env
   ```
   Edit `.env` with your configuration:
   ```env
   MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net
   MONGODB_DB_NAME=ecommerce
   SECRET_KEY=your-secret-key-here
   STRIPE_SECRET_KEY=sk_test_your_stripe_key
   AWS_ACCESS_KEY_ID=your-aws-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret
   ```

5. **Run the backend**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd ../frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Environment configuration**
   ```bash
   echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env
   ```

4. **Run the frontend**
   ```bash
   npm start
   ```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📊 Database Schema

### Collections Overview

| Collection | Purpose | Key Features |
|------------|---------|--------------|
| `products` | Product catalog | Variants, inventory, full-text search |
| `users` | User management | Authentication, addresses, preferences |
| `orders` | Order processing | Status tracking, payment info |
| `reviews` | Product reviews | Rating system, helpfulness voting |
| `carts` | Shopping carts | Session-based, auto-expiry |
| `categories` | Product categorization | Hierarchical structure |
| `stores` | Physical locations | Geospatial indexing |

### Key Indexes

```javascript
// Products - Text search and filtering
db.products.createIndex({
  "name": "text", 
  "description": "text", 
  "search_keywords": "text"
})

// Geospatial - Store locations
db.stores.createIndex({"location": "2dsphere"})

// Users - Authentication and location
db.users.createIndex({"email": 1}, {unique: true})
db.users.createIndex({"addresses.location": "2dsphere"})
```

## 🔐 Security Implementation

### Authentication & Authorization
- **JWT Tokens**: Secure token-based authentication
- **Password Security**: Bcrypt hashing with salt rounds
- **Token Refresh**: Automatic token refresh mechanism
- **Protected Routes**: Route-level access control

### Input Validation
- **Backend**: Pydantic models with type validation
- **Frontend**: Formik with Yup schema validation
- **API**: Request/response validation with automatic error handling

### Security Headers
- **CORS**: Configured for specific origins
- **HTTPS**: Force HTTPS in production
- **Rate Limiting**: API rate limiting (implementation ready)

## 🌍 Geospatial Features

The platform includes advanced geospatial capabilities using MongoDB's geospatial features:

### Store Locator
```javascript
// Find stores within 10km radius
db.stores.find({
  location: {
    $near: {
      $geometry: { type: "Point", coordinates: [longitude, latitude] },
      $maxDistance: 10000
    }
  }
})
```

### Product Availability by Location
```javascript
// Find nearby stores with specific product in stock
db.stores.aggregate([
  {
    $geoNear: {
      near: { type: "Point", coordinates: [lng, lat] },
      distanceField: "distance",
      maxDistance: 50000,
      query: {
        "inventory.product_id": productId,
        "inventory.quantity": { $gt: 0 }
      }
    }
  }
])
```

## 📈 Analytics & Reporting

### Sales Analytics
- Revenue trends by period
- Top-selling products
- Customer lifetime value
- Category performance

### Inventory Analytics
- Low stock alerts
- Inventory turnover
- Demand forecasting data

### Customer Analytics
- User behavior tracking
- Cart abandonment analysis
- Review sentiment analysis

## 🚀 Deployment Guide

### Backend Deployment (Railway/AWS ECS)

#### Railway Deployment
1. **Connect to Railway**
   ```bash
   npm install -g @railway/cli
   railway login
   railway init
   ```

2. **Configure environment variables**
   - Add all environment variables in Railway dashboard
   - Ensure MongoDB connection string is correct

3. **Deploy**
   ```bash
   railway up
   ```

#### AWS ECS Deployment
1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 8000
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Build and push to ECR**
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws-account>.dkr.ecr.us-east-1.amazonaws.com
   docker build -t ecom-backend .
   docker tag ecom-backend:latest <aws-account>.dkr.ecr.us-east-1.amazonaws.com/ecom-backend:latest
   docker push <aws-account>.dkr.ecr.us-east-1.amazonaws.com/ecom-backend:latest
   ```

### Frontend Deployment (Netlify/Vercel)

#### Netlify Deployment
1. **Build configuration**
   ```toml
   # netlify.toml
   [build]
   command = "npm run build"
   publish = "build"
   
   [build.environment]
   REACT_APP_API_URL = "https://your-backend-url.com/api/v1"
   ```

2. **Deploy**
   - Connect GitHub repository to Netlify
   - Configure build settings
   - Deploy automatically on push

#### Vercel Deployment
1. **Configuration**
   ```json
   {
     "buildCommand": "npm run build",
     "outputDirectory": "build",
     "devCommand": "npm start"
   }
   ```

2. **Environment Variables**
   - Add `REACT_APP_API_URL` in Vercel dashboard

### Database Deployment (MongoDB Atlas)

1. **Create MongoDB Atlas Cluster**
   - Choose appropriate tier (M0 free tier for development)
   - Configure network access and database users

2. **Import Data**
   ```bash
   mongoimport --uri "mongodb+srv://username:password@cluster.mongodb.net/ecommerce" --collection products --file sample_products.json
   ```

3. **Configure Indexes**
   - Run index creation scripts from `database/indexes.js`

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
# Database
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net
MONGODB_DB_NAME=ecommerce

# Security
SECRET_KEY=your-super-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# External Services
STRIPE_SECRET_KEY=sk_test_your_stripe_key
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET=your-s3-bucket

# Email (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### Frontend (.env)
```env
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
```

## 📝 API Documentation

### Authentication Endpoints
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `GET /api/v1/auth/me` - Get current user

### Product Endpoints
- `GET /api/v1/products/search` - Search products with filters
- `GET /api/v1/products/{id}` - Get product details
- `POST /api/v1/products` - Create product (admin)
- `PUT /api/v1/products/{id}` - Update product (admin)

### Cart Endpoints
- `GET /api/v1/cart` - Get user cart
- `POST /api/v1/cart/items` - Add item to cart
- `PATCH /api/v1/cart/items` - Update cart item
- `DELETE /api/v1/cart/items` - Remove item from cart

### Order Endpoints
- `POST /api/v1/orders` - Create order
- `GET /api/v1/orders` - Get user orders
- `GET /api/v1/orders/{id}` - Get order details

### Geospatial Endpoints
- `GET /api/v1/stores/search` - Find nearby stores
- `GET /api/v1/stores/nearby/{product_id}` - Find stores with product

For complete API documentation, visit `/docs` when running the backend.

## 🧪 Testing

### Backend Testing
```bash
cd backend
pytest tests/ -v
```

### Frontend Testing
```bash
cd frontend
npm test
```

### Load Testing
```bash
# Install artillery
npm install -g artillery

# Run load tests
artillery run tests/load-test.yml
```

## 🐛 Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   - Verify connection string in `.env`
   - Check network access in MongoDB Atlas
   - Ensure database user has proper permissions

2. **CORS Errors**
   - Update `BACKEND_CORS_ORIGINS` in backend configuration
   - Verify frontend URL is allowed

3. **JWT Token Issues**
   - Check `SECRET_KEY` configuration
   - Verify token expiration settings

4. **Build Errors**
   - Clear node_modules and reinstall: `rm -rf node_modules && npm install`
   - Check Node.js and Python versions

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Redux Toolkit Documentation](https://redux-toolkit.js.org/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

For questions and support:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation at `/docs`