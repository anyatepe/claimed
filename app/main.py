"""
Main FastAPI application with authentication middleware.
"""

from fastapi import FastAPI
from app.api.v1 import routes as v1_routes

app = FastAPI(
    title="API with Authentication",
    description="API with API key and JWT authentication",
    version="1.0.0"
)

# Include v1 routes (all protected by dependency injection)
app.include_router(v1_routes.router)
