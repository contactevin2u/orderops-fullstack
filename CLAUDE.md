# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a full-stack OrderOps application with three main components:

1. **Backend** (`/backend`) - FastAPI application with the following structure:
   - Main FastAPI app in `app/main.py` with routers for health, auth, orders, payments, export, documents, queue, reports, drivers, routes, and audit
   - Database models and migrations using Alembic
   - Authentication system with user management
   - Export functionality for cash payments with run tracking and rollback capability
   - Invoice PDF generation at `/_api/orders/<ID>/invoice.pdf`

2. **Frontend** (`/frontend`) - Next.js application with:
   - Tailwind CSS for styling
   - Authentication-protected pages (redirects unauthenticated users to `/login`)
   - Invoice printing at `/invoice/<ID>/print` (iframes backend PDF endpoint)
   - Cashier page for payment entry
   - Adjustments wizard for returns/buybacks/installment cancellations
   - Internationalization support (i18next)
   - Storybook for component development

3. **Driver App** (`/driver-app`) - Android application built with:
   - Kotlin and Jetpack Compose
   - Hilt for dependency injection
   - Room database for local storage
   - Offline-first architecture with AsyncStorage-backed outbox
   - Firebase integration (messaging, analytics, crashlytics)
   - Exponential backoff retry mechanism for offline requests
   - API client with Firebase ID token injection

## Development Commands

### Backend Development
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

### Backend Quality Checks
```bash
cd backend
pip install black flake8 mypy pytest pytest-cov
black --check .
flake8 .
mypy .
pytest --cov=app
```

### Frontend Development
```bash
cd frontend
npm ci
npm run dev
```

### Frontend Quality Checks
```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
npm run test  # Vitest tests
```

### Frontend Storybook
```bash
cd frontend
npm run storybook  # Runs on port 6006
npm run build-storybook
```

### Android Driver App
Build/development commands are managed via Gradle:
- Uses Kotlin 1.9.25, Android SDK 34
- Configured for Firebase App Distribution
- Requires `local.properties` with `API_BASE` property
- Release builds use `keystore.jks` if available, otherwise debug keystore

## Key Features

### Authentication & User Management
- First-time setup allows admin account creation at `/register`
- Default admin credentials available after migration
- All application pages require authentication

### Invoice System
- Invoice templates support QR codes via `payment.qrDataUrl`
- PDF generation through backend API
- Print interface in frontend

### Export & Cash Management
- Cash payment export API: `POST /export/cash` with date range and mark option
- Export run tracking: `GET /export/runs`, `GET /export/runs/{run_id}`, `POST /export/runs/{run_id}/rollback`

### Offline Support (Driver App)
- All HTTP requests routed through centralized client
- Offline requests stored in outbox with exponential backoff retry
- Toast notifications for errors and queued actions
- Automatic retry on connectivity restore or app foreground

## Database
- Uses Alembic for migrations
- Database models in backend with full schema management
- Room database for local storage in Android app

## Testing
- Backend: pytest with coverage reporting
- Frontend: Vitest for unit testing
- Type checking available for both TypeScript (frontend) and Python (backend)