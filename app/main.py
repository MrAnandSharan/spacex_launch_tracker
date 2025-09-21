from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.connection import redis_cache
from app.spacex.routers.data import router as data_router
from app.spacex.routers.statistics import router as statistics_router
import logging

version = "v1"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(name)s - %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_cache
    redis_cache.client.ping()
    yield
    if redis_cache and redis_cache.client:
        redis_cache.client.close()

app = FastAPI(
    title="SpaceX Launch Tracker",
    version=version,
    lifespan=lifespan
)

app.include_router(data_router, prefix=f"/api/{version}/launch")
app.include_router(statistics_router, prefix=f"/api/{version}/statistics")