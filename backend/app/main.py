import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, load_settings
from app.db import bootstrap_schema, create_pool


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        pool = create_pool(settings.database_url)
        await pool.open()
        await bootstrap_schema(pool)
        app.state.pool = pool
        yield
        await pool.close()

    app = FastAPI(title="Ya Sale", lifespan=lifespan)

    @app.get("/api/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    return app


def build_app() -> FastAPI:
    return create_app(load_settings(os.environ))
