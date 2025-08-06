# Deployment Guide

This document provides detailed deployment instructions for the e-commerce platform across different cloud providers and environments.

## 🏗️ Infrastructure Overview

### Recommended Production Architecture

```
Internet
    ↓
Load Balancer (AWS ALB / Cloudflare)
    ↓
Frontend (Netlify/Vercel)
    ↓
Backend API (AWS ECS / Railway / Google Cloud Run)
    ↓
Database (MongoDB Atlas)
    ↓
File Storage (AWS S3 / Cloudinary)
```

## 🌐 Frontend Deployment

### Netlify Deployment (Recommended)

1. **Prerequisites**
   - GitHub/GitLab repository
   - Node.js 16+ locally for testing

2. **Configuration**
   ```toml
   # netlify.toml
   [build]
   base = "frontend/"
   command = "npm run build"
   publish = "build"
   
   [build.environment]
   REACT_APP_API_URL = "https://your-backend-domain.com/api/v1"
   REACT_APP_STRIPE_PUBLISHABLE_KEY = "pk_live_your_stripe_key"
   
   [[redirects]]
   from = "/*"
   to = "/index.html"
   status = 200
   ```

3. **Deploy Steps**
   ```bash
   # Install Netlify CLI
   npm install -g netlify-cli
   
   # Login to Netlify
   netlify login
   
   # Deploy from project root
   cd ecom-platform
   netlify deploy --dir=frontend/build --prod
   ```

4. **Custom Domain Setup**
   - Add custom domain in Netlify dashboard
   - Configure DNS CNAME record
   - Enable HTTPS (automatic with Netlify)

### Vercel Deployment

1. **Configuration**
   ```json
   {
     "name": "ecom-frontend",
     "buildCommand": "cd frontend && npm run build",
     "outputDirectory": "frontend/build",
     "devCommand": "cd frontend && npm start",
     "installCommand": "cd frontend && npm install"
   }
   ```

2. **Deploy**
   ```bash
   # Install Vercel CLI
   npm install -g vercel
   
   # Deploy
   vercel --prod
   ```

## 🖥️ Backend Deployment

### AWS ECS Deployment (Production Recommended)

1. **Create Dockerfile**
   ```dockerfile
   # backend/Dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       && rm -rf /var/lib/apt/lists/*
   
   # Install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY . .
   
   # Create non-root user
   RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
   USER appuser
   
   EXPOSE 8000
   
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
   ```

2. **Build and Push to ECR**
   ```bash
   # Create ECR repository
   aws ecr create-repository --repository-name ecom-backend
   
   # Get login command
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   
   # Build and push
   cd backend
   docker build -t ecom-backend .
   docker tag ecom-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/ecom-backend:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/ecom-backend:latest
   ```

3. **ECS Task Definition**
   ```json
   {
     "family": "ecom-backend",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "256",
     "memory": "512",
     "executionRoleArn": "arn:aws:iam::<account>:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "ecom-backend",
         "image": "<account>.dkr.ecr.us-east-1.amazonaws.com/ecom-backend:latest",
         "portMappings": [
           {
             "containerPort": 8000,
             "protocol": "tcp"
           }
         ],
         "environment": [
           {
             "name": "MONGODB_URL",
             "value": "mongodb+srv://user:pass@cluster.mongodb.net"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/ecom-backend",
             "awslogs-region": "us-east-1",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

4. **ECS Service with ALB**
   ```bash
   # Create ECS cluster
   aws ecs create-cluster --cluster-name ecom-cluster
   
   # Create service
   aws ecs create-service \
     --cluster ecom-cluster \
     --service-name ecom-backend \
     --task-definition ecom-backend:1 \
     --desired-count 2 \
     --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=ecom-backend,containerPort=8000
   ```

### Railway Deployment (Quick & Easy)

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Deploy**
   ```bash
   cd backend
   railway init
   railway up
   ```

3. **Environment Variables**
   Set in Railway dashboard:
   - `MONGODB_URL`
   - `SECRET_KEY`
   - `STRIPE_SECRET_KEY`
   - All other required environment variables

### Google Cloud Run Deployment

1. **Build Container**
   ```bash
   cd backend
   gcloud builds submit --tag gcr.io/PROJECT-ID/ecom-backend
   ```

2. **Deploy**
   ```bash
   gcloud run deploy ecom-backend \
     --image gcr.io/PROJECT-ID/ecom-backend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars="MONGODB_URL=mongodb+srv://..."
   ```

## 🗄️ Database Deployment

### MongoDB Atlas (Recommended)

1. **Create Cluster**
   - Sign up at [MongoDB Atlas](https://cloud.mongodb.com)
   - Create new cluster (M0 free tier for development)
   - Choose cloud provider and region

2. **Security Configuration**
   ```bash
   # Database Access
   - Create database user with readWrite permissions
   - Use strong password or certificate authentication
   
   # Network Access
   - Add IP addresses (0.0.0.0/0 for development, specific IPs for production)
   - Configure VPC peering for enhanced security
   ```

3. **Connection String**
   ```bash
   mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/ecommerce?retryWrites=true&w=majority
   ```

4. **Indexes Setup**
   ```javascript
   // Connect to MongoDB and run these commands
   use ecommerce
   
   // Products collection indexes
   db.products.createIndex({
     "name": "text",
     "description": "text", 
     "search_keywords": "text",
     "brand": "text"
   })
   
   db.products.createIndex({"categories": 1, "status": 1})
   db.products.createIndex({"variants.price": 1})
   db.products.createIndex({"rating_summary.average_rating": -1})
   db.products.createIndex({"variants.sku": 1}, {unique: true})
   
   // Users collection indexes
   db.users.createIndex({"email": 1}, {unique: true})
   db.users.createIndex({"addresses.location": "2dsphere"})
   
   // Orders collection indexes
   db.orders.createIndex({"user_id": 1, "created_at": -1})
   db.orders.createIndex({"order_number": 1}, {unique: true})
   db.orders.createIndex({"status": 1, "created_at": -1})
   
   // Stores collection indexes
   db.stores.createIndex({"location": "2dsphere"})
   db.stores.createIndex({"store_id": 1}, {unique: true})
   ```

### Self-Hosted MongoDB

1. **Docker Deployment**
   ```yaml
   # docker-compose.yml
   version: '3.8'
   services:
     mongodb:
       image: mongo:6.0
       container_name: ecom-mongodb
       restart: always
       ports:
         - "27017:27017"
       environment:
         MONGO_INITDB_ROOT_USERNAME: admin
         MONGO_INITDB_ROOT_PASSWORD: password
         MONGO_INITDB_DATABASE: ecommerce
       volumes:
         - mongodb_data:/data/db
         - ./init-scripts:/docker-entrypoint-initdb.d
   
   volumes:
     mongodb_data:
   ```

2. **Kubernetes Deployment**
   ```yaml
   # mongodb-deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: mongodb
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: mongodb
     template:
       metadata:
         labels:
           app: mongodb
       spec:
         containers:
         - name: mongodb
           image: mongo:6.0
           ports:
           - containerPort: 27017
           env:
           - name: MONGO_INITDB_ROOT_USERNAME
             value: "admin"
           - name: MONGO_INITDB_ROOT_PASSWORD
             value: "password"
           volumeMounts:
           - name: mongodb-storage
             mountPath: /data/db
         volumes:
         - name: mongodb-storage
           persistentVolumeClaim:
             claimName: mongodb-pvc
   ```

## 🔐 Security Configuration

### SSL/TLS Certificate

1. **Cloudflare (Recommended)**
   - Add domain to Cloudflare
   - Enable "Full (strict)" SSL mode
   - Enable "Always Use HTTPS"
   - Configure firewall rules

2. **Let's Encrypt with Nginx**
   ```nginx
   server {
       listen 80;
       server_name api.yourdomain.com;
       return 301 https://$server_name$request_uri;
   }
   
   server {
       listen 443 ssl http2;
       server_name api.yourdomain.com;
       
       ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

### Environment Variables Security

1. **AWS Systems Manager Parameter Store**
   ```python
   import boto3
   
   def get_parameter(name):
       ssm = boto3.client('ssm')
       response = ssm.get_parameter(Name=name, WithDecryption=True)
       return response['Parameter']['Value']
   
   # Usage
   MONGODB_URL = get_parameter('/ecom/mongodb-url')
   SECRET_KEY = get_parameter('/ecom/secret-key')
   ```

2. **HashiCorp Vault**
   ```python
   import hvac
   
   client = hvac.Client(url='https://vault.example.com')
   client.token = os.environ['VAULT_TOKEN']
   
   secret = client.secrets.kv.v2.read_secret_version(path='ecom/config')
   MONGODB_URL = secret['data']['data']['mongodb_url']
   ```

## 📊 Monitoring and Logging

### Application Monitoring

1. **Sentry Setup**
   ```python
   # backend/main.py
   import sentry_sdk
   from sentry_sdk.integrations.fastapi import FastApiIntegration
   
   sentry_sdk.init(
       dsn="your-sentry-dsn",
       integrations=[FastApiIntegration(auto_enable=False)]
   )
   ```

2. **Datadog APM**
   ```python
   from ddtrace import patch_all
   patch_all()
   ```

### Infrastructure Monitoring

1. **AWS CloudWatch**
   ```yaml
   # cloudwatch-config.yaml
   metrics:
     namespace: EcomPlatform
     metrics_collected:
       cpu:
         measurement: [cpu_usage_idle, cpu_usage_iowait]
       disk:
         measurement: [used_percent]
       mem:
         measurement: [mem_used_percent]
   ```

2. **Prometheus + Grafana**
   ```yaml
   # prometheus.yml
   global:
     scrape_interval: 15s
   
   scrape_configs:
     - job_name: 'ecom-backend'
       static_configs:
         - targets: ['localhost:8000']
   ```

## 🚀 CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Build and push Docker image
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker build -t $ECR_REGISTRY/ecom-backend:$GITHUB_SHA backend/
          docker push $ECR_REGISTRY/ecom-backend:$GITHUB_SHA
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster ecom-cluster --service ecom-backend --force-new-deployment

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install and build
        run: |
          cd frontend
          npm ci
          npm run build
      
      - name: Deploy to Netlify
        uses: nwtgck/actions-netlify@v2
        with:
          publish-dir: './frontend/build'
          production-branch: main
          github-token: ${{ secrets.GITHUB_TOKEN }}
          deploy-message: "Deploy from GitHub Actions"
        env:
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
```

## 🔧 Performance Optimization

### Backend Optimization

1. **Gunicorn Configuration**
   ```python
   # gunicorn.conf.py
   bind = "0.0.0.0:8000"
   workers = 4
   worker_class = "uvicorn.workers.UvicornWorker"
   worker_connections = 1000
   max_requests = 1000
   max_requests_jitter = 100
   timeout = 30
   keepalive = 5
   ```

2. **Redis Caching**
   ```python
   import redis
   from fastapi_cache import FastAPICache
   from fastapi_cache.backends.redis import RedisBackend
   
   @app.on_event("startup")
   async def startup():
       redis_client = redis.from_url("redis://localhost:6379")
       FastAPICache.init(RedisBackend(redis_client), prefix="ecom")
   ```

### Frontend Optimization

1. **Webpack Bundle Analysis**
   ```bash
   npm install -g webpack-bundle-analyzer
   npx webpack-bundle-analyzer build/static/js/*.js
   ```

2. **Code Splitting**
   ```typescript
   // Lazy load components
   const ProductDetail = lazy(() => import('./pages/ProductDetailPage'));
   const Cart = lazy(() => import('./pages/CartPage'));
   ```

### Database Optimization

1. **Connection Pooling**
   ```python
   # MongoDB connection with pooling
   client = AsyncIOMotorClient(
       MONGODB_URL,
       maxPoolSize=50,
       minPoolSize=10,
       maxIdleTimeMS=30000
   )
   ```

2. **Query Optimization**
   ```python
   # Use projections to limit returned fields
   products = await Product.find(
       Product.status == "active"
   ).project(ProductSummary).to_list()
   ```

## 🧪 Testing in Production

### Health Checks

```python
@app.get("/health")
async def health_check():
    try:
        # Check database connection
        await db.client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service unavailable")
```

### Load Testing

```bash
# Artillery load test
artillery run --target https://api.yourdomain.com tests/load-test.yml
```

## 📱 Mobile Considerations

### Progressive Web App (PWA)

1. **Service Worker**
   ```javascript
   // public/sw.js
   const CACHE_NAME = 'ecom-v1';
   const urlsToCache = [
     '/',
     '/static/js/bundle.js',
     '/static/css/main.css'
   ];
   
   self.addEventListener('install', event => {
     event.waitUntil(
       caches.open(CACHE_NAME)
         .then(cache => cache.addAll(urlsToCache))
     );
   });
   ```

2. **Web App Manifest**
   ```json
   {
     "short_name": "EcomPlatform",
     "name": "EcomPlatform - Shop Smart",
     "icons": [
       {
         "src": "favicon.ico",
         "sizes": "64x64 32x32 24x24 16x16",
         "type": "image/x-icon"
       }
     ],
     "start_url": ".",
     "display": "standalone",
     "theme_color": "#3b82f6",
     "background_color": "#ffffff"
   }
   ```

## 💰 Cost Optimization

### Development Environment
- **Frontend**: Netlify (Free tier)
- **Backend**: Railway (Free tier)
- **Database**: MongoDB Atlas M0 (Free tier)
- **Total**: $0/month

### Production Environment (Small Scale)
- **Frontend**: Netlify Pro ($19/month)
- **Backend**: AWS ECS Fargate (~$30/month)
- **Database**: MongoDB Atlas M10 ($57/month)
- **CDN**: Cloudflare Pro ($20/month)
- **Total**: ~$126/month

### Production Environment (Medium Scale)
- **Frontend**: Netlify Pro ($19/month)
- **Backend**: AWS ECS Fargate with ALB (~$100/month)
- **Database**: MongoDB Atlas M30 ($157/month)
- **Cache**: Redis ElastiCache ($50/month)
- **Monitoring**: Datadog ($15/month)
- **Total**: ~$341/month

## 🚨 Disaster Recovery

### Backup Strategy

1. **Database Backups**
   - MongoDB Atlas: Automatic backups included
   - Self-hosted: Use mongodump with cron jobs

2. **Application Backups**
   - Code: Git repositories (GitHub/GitLab)
   - Assets: S3 with versioning enabled

### Recovery Procedures

1. **Database Recovery**
   ```bash
   # Restore from Atlas backup
   # Use Atlas UI or mongorestore command
   
   # Self-hosted recovery
   mongorestore --uri="mongodb://localhost:27017" --db=ecommerce backup/
   ```

2. **Application Recovery**
   ```bash
   # Redeploy from last known good commit
   git checkout <commit-hash>
   
   # Trigger deployment pipeline
   git tag -a recovery-$(date +%s) -m "Recovery deployment"
   git push origin recovery-$(date +%s)
   ```

This deployment guide provides comprehensive instructions for deploying the e-commerce platform across various cloud providers with production-ready configurations.