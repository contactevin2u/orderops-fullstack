from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from .core.config import settings, cors_origins_list
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
    trips,
)

app = FastAPI(title="OrderOps Fullstack v1", default_response_class=ORJSONResponse)

origins = cors_origins_list() or ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(parse.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(export.router)
app.include_router(documents.router)
app.include_router(queue.router)
app.include_router(reports.router)
app.include_router(drivers.router)
app.include_router(trips.router)
