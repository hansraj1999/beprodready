from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.firebase_app import init_firebase, shutdown_firebase
from app.core.logging import setup_logging
from app.db.session import engine
from app.middleware.firebase_auth import FirebaseAuthMiddleware

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_firebase()
    yield
    shutdown_firebase()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Archai API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.ENV != "production" else None,
        redoc_url="/redoc" if settings.ENV != "production" else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(FirebaseAuthMiddleware)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
