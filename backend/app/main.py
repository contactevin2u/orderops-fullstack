import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables first
load_dotenv()

from .core.config import settings, cors_origins_list
from .routers import auth as auth_router
from .routers import (
    health,
    parse,
    orders,
    payments,
    export,
    documents,
    queue,
    reports,
    drivers,
    routes as routes_router,
    shifts,
    ai_assignments,
    driver_schedule,
    unified_assignments,
    debug,
)
from .audit import router as audit_router

# Ensure uploads directory exists for static file serving
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="OrderOps Fullstack v1", default_response_class=ORJSONResponse)

origins = cors_origins_list() or ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(health.router)
app.include_router(auth_router.router)
app.include_router(parse.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(export.router)
app.include_router(documents.router)
app.include_router(queue.router)
app.include_router(reports.router)
app.include_router(drivers.router)
app.include_router(routes_router.router)
app.include_router(shifts.router)
app.include_router(ai_assignments.router)
app.include_router(driver_schedule.router)
app.include_router(unified_assignments.router)
app.include_router(debug.router)
app.include_router(audit_router)
