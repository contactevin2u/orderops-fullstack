# OrderOps Full Stack

This repository contains a FastAPI backend and a Next.js frontend. The CI workflow checks code style, types, tests and build for both parts.

## Authentication

All application pages require a logged-in user and unauthenticated visitors are redirected to `/login`.

During the first run you can create an administrator account at `/register`. After running the migration that adds user support, a default admin user exists:


Administrators can sign in with these credentials and create additional users.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

## Running checks locally

### Backend

```bash
cd backend
pip install -r requirements.txt
pip install black flake8 mypy pytest pytest-cov
black --check .
flake8 .
mypy .
pytest --cov=app
```

### Frontend

```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

## Invoice Rendering

The frontend was bootstrapped with Next.js and uses Tailwind CSS for styling.
Install the dependencies and start the development server:

```bash
cd frontend
npm install tailwindcss puppeteer
npm run dev
```

To produce a printable PDF for an invoice, run the render script in another
terminal. The invoice ID defaults to the first CLI argument but can be
overridden with the `INVOICE_ID` environment variable:

```bash
cd frontend
INVOICE_ID=123 npx tsx ../scripts/render-invoice.ts
```

The script opens `http://localhost:3000/invoice/<ID>/print` in a headless
browser and writes `invoice-<ID>.pdf` with A4 margins and backgrounds
included. Invoice templates can embed QR codes by using `payment.qrDataUrl`
as the image source.

## Export Runs

The backend supports marking cash payment exports so they are not exported twice.
Use the JSON endpoint:

```
POST /export/cash {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "mark": true}
```

Marked payments are associated with a run ID and timestamp. You can list past
runs via `GET /export/runs`, inspect their payments with
`GET /export/runs/{run_id}`, or rollback a run using
`POST /export/runs/{run_id}/rollback`.

The frontend now includes a **Cashier** page for quick payment entry and an
**Adjustments** wizard for returns, buybacks and installment cancellations.
