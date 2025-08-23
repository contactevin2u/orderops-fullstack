# Backend (FastAPI + Postgres) — OrderOps Full Stack

- Orders, Items, Plans (RENTAL/INSTALLMENT), Payments (POSTED/VOIDED)
- Documents: invoice (with terms & bank info), receipt, installment agreement (simple PDFs)
- Export: cash-basis payments to Excel (``/export/cash.xlsx`` or ``/export/payments_received.xlsx``)

## Local dev (Windows)
```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
# if local DB configured:
alembic upgrade head
```

## Environment variables

- `FIREBASE_SERVICE_ACCOUNT_JSON`: JSON string for Firebase service account used to verify driver ID tokens.

## Worker configuration

The background worker polls the database for queued jobs and can be configured
via environment variables or command-line flags:

| Option | Env var | Flag | Default |
|--------|---------|------|---------|
| Polling interval (seconds) | `WORKER_POLL_SECS` | `--poll-interval` | `1.0` |
| Batch size | `WORKER_BATCH_SIZE` | `--batch-size` | `10` |
| Max attempts per job | `WORKER_MAX_ATTEMPTS` | `--max-attempts` | `5` |

Example:

```bash
python -m app.worker --poll-interval 2 --batch-size 5
```
