# OrderOps Full Stack

This repository contains a FastAPI backend and a Next.js frontend. The CI workflow checks code style, types, tests and build for both parts.

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
