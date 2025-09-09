# OrderOps - Full Stack Delivery Management System

A comprehensive delivery and inventory management system with UID tracking, route optimization, and real-time order processing. Built with FastAPI (Python), Next.js (React), and Android (Kotlin).

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Driver App    │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (Android)     │
│                 │    │                 │    │                 │
│ • Admin Portal  │    │ • REST APIs     │    │ • Job Management│
│ • Order Mgmt    │    │ • UID Tracking  │    │ • QR Scanning   │
│ • UID Generator │    │ • Route Mgmt    │    │ • Delivery POD  │
│ • Reporting     │    │ • Commission    │    │ • Stock Verify  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Database      │
                    │ (PostgreSQL)    │
                    │                 │
                    │ • Orders        │
                    │ • Customers     │
                    │ • Inventory     │
                    │ • UID Tracking  │
                    │ • Commissions   │
                    └─────────────────┘
```

## 🚀 Key Features

### 📦 Advanced UID Inventory System
- **Comprehensive UID Generation**: Auto-generates unique identifiers for all inventory items
- **QR Code Integration**: Generate, print, and scan QR codes for seamless tracking
- **Multi-Action Tracking**: LOAD_OUT, DELIVER, RETURN, REPAIR, SWAP, LOAD_IN actions
- **Real-time Validation**: Prevents duplicate scans with idempotent operations
- **Audit Trail**: Complete transaction history with driver attribution

### 🚛 Driver Management & Route Optimization
- **Smart Route Assignment**: Automatic driver assignment with secondary driver support
- **Real-time Job Tracking**: Live status updates (ASSIGNED → IN_TRANSIT → DELIVERED)
- **Mandatory UID Scanning**: Enforce compliance before delivery completion
- **Proof of Delivery**: Photo capture with GPS location tracking
- **Offline Support**: Queue actions when connectivity is lost

### 💼 Order & Commission Management
- **Advanced Order Parsing**: AI-powered message parsing for order creation
- **Flexible Payment Tracking**: Multiple payment methods with export capabilities
- **Commission Calculation**: Automated driver commission with split support
- **Outstanding Reports**: Real-time balance tracking and collection management
- **Return/Buyback Workflow**: Complete order lifecycle management

### 📱 Mobile-First Design
- **Android Driver App**: Native Kotlin app with Jetpack Compose UI
- **QR Code Scanning**: Continuous scanning with validation feedback
- **GPS Integration**: Accurate location tracking for deliveries
- **Firebase Integration**: Push notifications, analytics, and crash reporting
- **Offline-First Architecture**: Robust operation without internet connectivity

## 🛠️ Technology Stack

### Backend (`/backend`)
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migration**: Alembic for database schema management
- **Authentication**: Firebase Authentication with JWT tokens
- **File Storage**: Cloud storage integration for POD photos
- **Background Jobs**: Async task processing
- **API Documentation**: Auto-generated OpenAPI/Swagger docs

### Frontend (`/frontend`)
- **Framework**: Next.js 14+ with TypeScript
- **Styling**: Tailwind CSS with custom components
- **State Management**: React hooks with SWR for data fetching
- **Authentication**: Firebase Auth integration
- **Internationalization**: i18next for multi-language support
- **Development**: Storybook for component development

### Driver App (`/driver-app`)
- **Platform**: Android (API 24+, targeting API 35)
- **Language**: Kotlin with Jetpack Compose
- **Architecture**: MVVM with Repository pattern
- **Database**: Room for local storage
- **Networking**: Retrofit with OkHttp
- **Dependency Injection**: Hilt
- **Camera**: CameraX for QR code scanning
- **Location**: Fused Location Provider

## 🚀 Quick Start

### Prerequisites
- **Node.js** 18+ and npm/yarn
- **Python** 3.11+ with pip
- **PostgreSQL** 13+ database
- **Android Studio** (for driver app development)
- **Firebase Project** with Authentication enabled

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database and Firebase credentials

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm ci

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with your API endpoints

# Start development server
npm run dev
```

### Driver App Setup
```bash
cd driver-app

# Configure API endpoint
echo "API_BASE=http://your-api-url" >> local.properties

# Build and install
./gradlew assembleDebug
./gradlew installDebug
```

## 🔧 Development Commands

### Backend Quality & Testing
```bash
cd backend
pip install black flake8 mypy pytest pytest-cov

# Code formatting
black --check .
black .

# Linting
flake8 .

# Type checking
mypy .

# Run tests with coverage
pytest --cov=app tests/
```

### Frontend Quality & Testing
```bash
cd frontend

# Linting
npm run lint
npm run lint:fix

# Type checking
npx tsc --noEmit

# Build verification
npm run build

# Unit tests
npm run test

# Component development
npm run storybook
```

### Android Driver App
```bash
cd driver-app

# Debug build
./gradlew assembleDebug

# Release build (requires keystore configuration)
./gradlew assembleRelease

# Run tests
./gradlew test

# Code analysis
./gradlew lint
```

## 📊 API Documentation

### Core Endpoints

#### Authentication
- `POST /auth/login` - User authentication
- `GET /auth/me` - Get current user profile
- `POST /auth/refresh` - Refresh authentication token

#### Orders Management
- `GET /orders` - List orders with filtering
- `POST /orders` - Create new order (supports parsed input)
- `GET /orders/{id}` - Get order details
- `PATCH /orders/{id}` - Update order status
- `POST /orders/{id}/void` - Cancel/void order

#### UID Inventory System
- `GET /inventory/config` - Get inventory system configuration
- `POST /inventory/generate-uid` - Generate UIDs for SKUs
- `POST /inventory/uid/scan` - Record UID scan actions
- `GET /orders/{id}/uids` - Get UID history for order
- `POST /inventory/generate-qr` - Generate QR codes

#### Driver Operations
- `GET /drivers/jobs` - Get assigned driver jobs
- `PATCH /drivers/orders/{id}` - Update delivery status (with UID actions)
- `POST /drivers/orders/{id}/pod-photo` - Upload proof of delivery
- `GET /drivers/commissions` - Get driver commission summary

#### Reporting & Export
- `GET /reports/outstanding` - Outstanding balance reports
- `GET /export/cash.xlsx` - Export payment data
- `GET /drivers/{id}/lorry-stock/{date}` - Lorry stock reports

Full API documentation available at `/docs` when running the backend server.

## 🗄️ Database Schema

### Core Tables
- **orders**: Order information with customer details
- **order_items**: Line items within orders
- **order_item_uid**: UID tracking for inventory items
- **drivers**: Driver profiles and authentication
- **trips**: Delivery assignments and route tracking
- **payments**: Payment records and export tracking
- **commissions**: Driver commission calculations

### UID Inventory Tables
- **items**: Physical inventory items with UIDs
- **sku**: Stock Keeping Units (product definitions)
- **sku_alias**: Alternative names for SKU matching
- **lorry_stock**: Daily driver stock verification

## 🔐 Security & Authentication

### Firebase Authentication
- **JWT Tokens**: Secure API access with Firebase ID tokens
- **Role-Based Access**: Admin, Driver, Cashier role separation
- **Session Management**: Automatic token refresh and validation

### Data Security
- **Input Validation**: Comprehensive request validation with Pydantic
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **File Upload Security**: Validated image uploads with size limits
- **Audit Logging**: Complete action history for compliance

## 🚀 Deployment

### Production Environment Variables

#### Backend (.env)
```env
DATABASE_URL=postgresql://user:pass@host:5432/orderops
FIREBASE_PROJECT_ID=your-firebase-project
FIREBASE_PRIVATE_KEY_PATH=/path/to/firebase-key.json
STORAGE_BUCKET=your-storage-bucket
UID_INVENTORY_ENABLED=true
UID_SCAN_REQUIRED_AFTER_POD=true
```

#### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXT_PUBLIC_FIREBASE_CONFIG={"apiKey":"...","authDomain":"..."}
```

#### Android App (local.properties)
```properties
API_BASE=https://your-api-domain.com
KEYSTORE_PASSWORD=your-keystore-password
KEY_ALIAS=your-key-alias  
KEY_PASSWORD=your-key-password
```

### Docker Deployment
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/orderops
    ports:
      - "8000:8000"
    
  frontend:
    build: ./frontend  
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    ports:
      - "3000:3000"
      
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=orderops
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 🧪 Testing Strategy

### Backend Testing
- **Unit Tests**: Service layer and utility functions
- **Integration Tests**: API endpoints and database operations
- **UID System Tests**: Complete UID workflow validation
- **Commission Tests**: Payment calculation accuracy

### Frontend Testing  
- **Component Tests**: React component functionality
- **API Integration**: Frontend-backend communication
- **User Workflow**: Complete user journey testing

### Driver App Testing
- **Unit Tests**: Business logic and data models
- **UI Tests**: Compose component testing
- **Integration Tests**: API communication and offline sync
- **GPS/Camera Tests**: Hardware feature integration

## 📈 Monitoring & Analytics

### Application Monitoring
- **Backend**: FastAPI built-in metrics and logging
- **Frontend**: Next.js performance monitoring
- **Mobile**: Firebase Crashlytics and Analytics

### Business Metrics
- **Order Processing**: Delivery completion rates
- **Driver Performance**: Commission and efficiency tracking
- **Inventory Accuracy**: UID scanning compliance rates
- **Customer Satisfaction**: Delivery time and success metrics

## 🤝 Contributing

### Development Workflow
1. **Fork Repository**: Create your feature branch
2. **Code Standards**: Follow linting and formatting rules
3. **Testing**: Ensure all tests pass before submitting
4. **Documentation**: Update relevant documentation
5. **Pull Request**: Submit PR with detailed description

### Code Style Guidelines
- **Python**: Black formatting, PEP 8 compliance
- **TypeScript**: ESLint + Prettier configuration
- **Kotlin**: ktlint with Android coding standards

## 📋 System Requirements

### Development Environment
- **OS**: Windows 10+, macOS 11+, or Ubuntu 20.04+
- **Memory**: 8GB RAM minimum, 16GB recommended
- **Storage**: 10GB free space for all dependencies
- **Network**: Stable internet for Firebase and API testing

### Production Environment
- **Backend**: 2GB RAM, 2 CPU cores, PostgreSQL 13+
- **Frontend**: CDN deployment (Vercel, Netlify)
- **Database**: 4GB RAM, SSD storage, automated backups
- **Mobile**: Android 7.0+ (API 24), Camera, GPS, Internet

## 🐛 Troubleshooting

### Common Issues

#### Backend Issues
- **Database Connection**: Check DATABASE_URL format and PostgreSQL service
- **Firebase Auth**: Verify FIREBASE_PROJECT_ID and credentials file
- **Migration Errors**: Run `alembic upgrade head` to apply latest schema

#### Frontend Issues  
- **API Connection**: Verify NEXT_PUBLIC_API_URL matches backend address
- **Authentication**: Check Firebase configuration and project settings
- **Build Errors**: Clear `.next` cache and reinstall node_modules

#### Driver App Issues
- **API Connection**: Verify API_BASE in local.properties
- **QR Scanning**: Check camera permissions and ZXing library integration
- **GPS Issues**: Ensure location permissions and Google Play Services

## 📞 Support & Contact

### Documentation
- **API Docs**: Available at `/docs` endpoint when backend is running
- **Component Library**: Run `npm run storybook` in frontend directory
- **Architecture Diagrams**: Located in `/docs` directory

### Community
- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and ideas
- **Wiki**: Comprehensive guides and troubleshooting

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**OrderOps** - Streamlining delivery operations with modern technology and intelligent automation.