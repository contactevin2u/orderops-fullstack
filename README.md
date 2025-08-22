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
