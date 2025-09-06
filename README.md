# OrderOps - Complete Order Management System

A comprehensive full-stack order management system with automated AI assignment, real-time inventory tracking, and integrated financial processing.

## 🏗️ Architecture Overview

**3-Tier Full-Stack Application:**
- **Backend**: FastAPI with PostgreSQL, AI-powered assignment, real-time processing
- **Frontend**: Next.js with Tailwind CSS, real-time admin interface
- **Mobile**: Android driver app with offline-first architecture

## 🔄 Complete Order Flow

### 1. **ORDER PARSING STAGE** (`/parse/*`)

**4-Stage LLM Classification Pipeline:**
- **Stage 1**: Text input parsing (WhatsApp messages, manual input)  
- **Stage 2**: Order type identification (OUTRIGHT | INSTALLMENT | RENTAL | MIXED)
- **Stage 3**: Status determination (NEW | ACTIVE | RETURNED | CANCELLED | COMPLETED)
- **Stage 4**: Financial category classification (ORDER | RENTAL | INSTALLMENT | PENALTY | DELIVERY | BUYBACK)

**Processing Branches:**
```
Input → Parse → {
  ├─ OUTRIGHT → Direct sale
  ├─ INSTALLMENT → Payment plan setup  
  ├─ RENTAL → Recurring billing
  ├─ MIXED → Hybrid approach
  └─ ADJUSTMENT → Return/Buyback/Cancellation
}
```

**Endpoints:**
- `POST /parse/advanced` - Full 4-stage LLM parsing
- `POST /parse/classify` - Message classification only
- `POST /parse/quotation` - Quotation parsing
- `POST /parse/find-order` - Mother order lookup

### 2. **ORDER CREATION & RECORDING** (`/orders/*`)

**Data Flow:**
- Customer creation/lookup with deduplication
- Order record with Decimal precision financial calculations
- Item breakdown and pricing with line totals
- Payment plan setup (installments/rentals)
- Idempotency handling for duplicate prevention

**Financial Precision:**
```python
subtotal: Decimal = Decimal("0.00")  # 12,2 precision
total: Decimal = calculated_subtotal + delivery_fee - discount
balance: Decimal = total - paid_amount
```

### 3. **🤖 FULLY AUTOMATED AI ASSIGNMENT**

**CRITICAL**: Every order creation **automatically triggers** PhD-level AI assignment:

```python
# Triggered immediately after order creation
trigger_auto_assignment(db, order.id)
  ↓
AssignmentService.auto_assign_all()
  ↓ 
GPT-4 PhD-level route optimization
```

**Assignment Intelligence:**
- **Driver Selection**: ONLY scheduled drivers (DriverSchedule integration)
- **Priority System**: Clocked-in > Scheduled > Workload balancing
- **Geographic AI**: Malaysian logistics expertise (Plus Highway, state corridors)
- **Route Optimization**: Multi-depot vehicle routing (MD-VRP) algorithms
- **Real-time**: Both synchronous assignment + background queue processing

**AI Optimization Features:**
- **Route Clustering**: North/South/East corridor grouping
- **Fuel Efficiency**: Minimizes total fleet costs and driver hours  
- **Area Familiarity**: Uses driver delivery history for optimal assignment
- **Sabah Logistics**: Separate Kota Kinabalu base coordination

### 4. **DRIVER APP INTEGRATION** 📱

**Real-time Driver Journey:**
- **Clock System**: In/out tracking with outstation detection
- **Job Management**: Real-time order retrieval and status updates
- **Location Services**: GPS pinging with accuracy tracking
- **Order Progression**: Status updates (ASSIGNED → IN_TRANSIT → DELIVERED)
- **POD System**: Multiple proof-of-delivery photos
- **Stock Reconciliation**: `/drivers/{id}/lorry-stock/{date}` integration

**Offline-First Architecture:**
- Outbox pattern with exponential backoff retry
- AsyncStorage-backed request queuing
- Firebase integration (messaging, analytics, crashlytics)
- Automatic connectivity restoration

### 5. **DELIVERY EXECUTION & STATUS MANAGEMENT**

**Status Progression:**
```
NEW → ASSIGNED → IN_TRANSIT → {
  ├─ DELIVERED → Success path → Commission calculation
  ├─ RETURNED → Failed delivery → Return processing
  ├─ ON_HOLD → Customer issues → Hold management
  └─ CANCELLED → Order cancellation → Adjustment handling
}
```

**Advanced Features:**
- **Upsell During Delivery**: Driver-initiated item upgrades
- **Dynamic Hold Management**: Customer issue resolution
- **Return Processing**: Automated adjustment order creation
- **Real-time Tracking**: Location and status monitoring

### 6. **ENHANCED UID INVENTORY SYSTEM** 📦

**7-Action Lifecycle Management:**
```
Order → UID Actions → {
  ├─ LOAD_OUT → Driver takes inventory from warehouse
  ├─ DELIVER → Customer receives items (with POD)
  ├─ RETURN → Items returned from customer  
  ├─ REPAIR → Maintenance/service required
  ├─ SWAP → Item exchange during delivery
  ├─ LOAD_IN → Items returned to warehouse
  └─ ISSUE → Problem/damage reporting
}
```

**Integration Points:**
- **Driver App**: Real-time UID scanning with order linking
- **Backend**: `/inventory/uid/scan` with enhanced action support
- **SKU Resolution**: Fuzzy matching and alias support
- **Stock Reconciliation**: Daily driver stock verification
- **Item Tracking**: Current location and status per UID

### 7. **FINANCIAL BACKBONE & ACCRUALS** 💰

**Precision Financial System:**
- **Decimal Arithmetic**: All monetary calculations use Decimal(12,2)
- **Commission System**: PENDING → ACTUALIZED workflow
- **Accrual Accuracy**: Proper monthly calculation and tracking
- **Multi-category Support**: ORDER/RENTAL/INSTALLMENT/PENALTY/DELIVERY/BUYBACK

**Commission Flow:**
```
Order Completion → Commission Calculation → {
  ├─ Pending State → Awaiting actualization conditions
  ├─ Actualized → Commission released to driver
  └─ Scheme-based → Rate calculation (flat/percentage)
}
```

**Export & Reconciliation:**
- Cash payment export with run tracking
- Rollback capabilities for export corrections
- QR code receipt generation
- Invoice PDF generation at `/orders/{id}/invoice.pdf`

### 8. **PAYMENT RECORDING & CATEGORIZATION**

**Payment Categories:**
- **ORDER**: Direct order payments
- **RENTAL**: Monthly rental fees  
- **INSTALLMENT**: Scheduled payment plan payments
- **PENALTY**: Late fees and penalties
- **DELIVERY**: Delivery and logistics charges
- **BUYBACK**: Return transaction payments

**Payment Processing:**
- Idempotency key support
- Export run tracking
- Void/rollback capabilities
- Multi-method support (cash/transfer/cheque)

### 9. **ADVANCED DRIVER FEATURES**

**Upsell System:**
- Driver-initiated upsells during delivery
- BELI_TERUS (outright purchase) conversion
- ANSURAN (installment) plan modifications
- Incentive tracking and commission calculation

**Hold Management:**
- Put orders on hold for customer issues
- Resolution workflow with notes
- Automatic status restoration
- Hold reason categorization

### 10. **ORDER COMPLETION & COMMISSION**

**Final State Processing:**
- Order marked as COMPLETED with timestamp
- Commission calculation and actualization
- Payment reconciliation and balance updates
- Inventory status synchronization
- Performance metrics update

## 🚀 Development & Deployment

### **Local Development**

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm ci
npm run dev
```

**Worker Process:**
```bash
cd backend
python -m app.worker
```

### **Environment Configuration**

**Required Variables:**
```bash
DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require
JWT_SECRET=********************************
FIREBASE_SERVICE_ACCOUNT_JSON={"type": "service_account", "project_id": "your-project"}
OPENAI_API_KEY=sk-********************************
ADMIN_EMAILS=admin@yourcompany.com
```

### **Render Cloud Deployment**

**Backend Build:**
```bash
pip install -r backend/requirements.txt
python migrate.py  # Automated migration handling
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Frontend Build:**
```bash
cd frontend && npm ci && npm run build
```

### **Database Migrations**

**Current Migration Head:** `c4f8e2a91b12` (Enhanced UID System)

**Production Migration:**
```bash
python migrate.py  # Handles PostgreSQL URL conversion and SSL
```

## 🧪 Testing & Quality

**Comprehensive Testing:**
```bash
# Full system integration test
python test_order_flow.py

# Backend quality checks
cd backend
black --check .
flake8 .
mypy .
pytest --cov=app

# Frontend quality checks  
cd frontend
npm run lint
npx tsc --noEmit
npm run build
npm run test
```

## 🔐 Authentication & Security

**Authentication System:**
- Firebase integration with JWT tokens
- Role-based access control (ADMIN, CASHIER, DRIVER)
- First-time admin account creation at `/register`
- All application pages require authentication

**Security Features:**
- Idempotency key support for duplicate prevention
- Audit logging for all critical operations
- Secure API token injection in mobile app
- SSL/TLS enforcement in production

## 📊 Key Features

### **AI-Powered Operations**
- ✅ **PhD-level route optimization** with Malaysian geography expertise
- ✅ **Automated assignment** triggered on every order creation
- ✅ **WhatsApp parsing** with 4-stage LLM classification
- ✅ **Intelligent scheduling** integration with driver availability

### **Real-time Integration**
- ✅ **Driver app synchronization** with offline-first architecture
- ✅ **Live order tracking** with GPS location services
- ✅ **Instant status updates** across all system components
- ✅ **Background processing** with queue system and retry logic

### **Financial Accuracy**
- ✅ **Decimal precision** for all monetary calculations
- ✅ **Multi-category payment** support with proper reconciliation
- ✅ **Commission tracking** with pending/actualized workflow
- ✅ **Export capabilities** with rollback and audit trails

### **Advanced Inventory**
- ✅ **UID-level tracking** with 7-action lifecycle management
- ✅ **Stock reconciliation** between driver app and backend
- ✅ **SKU resolution** with fuzzy matching and aliases
- ✅ **Real-time scanning** integration with order fulfillment

### **Enterprise Features**
- ✅ **Multi-platform support** (Web admin + Android driver app)
- ✅ **Offline-first mobile** with automatic sync
- ✅ **Invoice generation** with QR code support
- ✅ **Export/import** capabilities with audit trails
- ✅ **Performance monitoring** and comprehensive logging

## 📱 Mobile App Features

**Driver App (Android):**
- Kotlin + Jetpack Compose architecture
- Offline-first with outbox pattern
- Firebase integration (messaging, analytics, crashlytics)
- Real-time GPS tracking and location services
- Multi-photo POD capture
- UID inventory scanning
- Commission tracking and upsell management

**Build Configuration:**
```bash
# Android development
./gradlew compileDebugKotlin
./gradlew assembleDebug

# Release build
./gradlew assembleRelease
```

## 🎯 Production Readiness

**✅ FULLY INTEGRATED SYSTEM:**
- **Order Flow**: Parsing → Creation → **Auto AI Assignment** → Delivery → Commission
- **Mobile Integration**: Full driver app compatibility with enhanced features
- **Financial Backbone**: Accurate calculations with proper decimal handling
- **Inventory Tracking**: Complete UID system with stock reconciliation
- **Real-time Operations**: Live updates and background processing

**🚀 RENDER DEPLOYMENT READY**
- Migration scripts prepared for PostgreSQL with SSL
- Environment configuration documented  
- Quality checks and testing framework complete
- Comprehensive integration validation passed

---

*This system provides complete end-to-end order management with AI-powered automation, real-time mobile integration, and enterprise-grade financial processing - ready for production deployment on Render cloud platform.*