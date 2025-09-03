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
    driver,
    drivers,
    driver_orders,
    routes as routes_router,
    shifts,
    driver_schedule,
    assignment,
    debug,
    debug_trace,
    upsells,
    admin_master,
)
from .audit import router as audit_router

# No longer need uploads directory - using Firebase Storage only

app = FastAPI(title="OrderOps Fullstack v1", default_response_class=ORJSONResponse)

origins = cors_origins_list() or ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No static file serving needed - all images served from Firebase Storage

app.include_router(health.router)
app.include_router(auth_router.router)
app.include_router(parse.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(export.router)
app.include_router(documents.router)
app.include_router(queue.router)
app.include_router(reports.router)
app.include_router(driver.router)
app.include_router(drivers.router)
app.include_router(driver_orders.router)
app.include_router(routes_router.router)
app.include_router(shifts.router)
app.include_router(driver_schedule.router)
app.include_router(assignment.router)
app.include_router(debug.router)
app.include_router(debug_trace.router)
app.include_router(upsells.router)
app.include_router(admin_master.router)
app.include_router(audit_router)
