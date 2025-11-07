from fastapi import FastAPI
from app.api.routes import core

app = FastAPI()

app.include_router(core.router, tags=["core"])
