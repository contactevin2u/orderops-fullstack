# Backend (FastAPI + Postgres) — OrderOps Full Stack

- Queue-driven parsing using Postgres `FOR UPDATE SKIP LOCKED`
- OpenAI structured parsing with heuristic fallback when the OpenAI API is unavailable
- Orders, Items, Plans (RENTAL/INSTALLMENT), Payments (POSTED/VOIDED)
- Documents: invoice, receipt, installment agreement (simple PDFs)
- Export: cash-basis payments to Excel

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
