"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import auth, resources, actions, cost, audit, accounts, health
from app.database import init_db, close_db
from app.cache import init_cache, close_cache

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    await init_db()
    await init_cache()
    yield
    # Shutdown
    await close_db()
    await close_cache()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Production-ready AWS resource management platform",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(resources.router, prefix="/api/resources", tags=["Resources"])
app.include_router(actions.router, prefix="/api/actions", tags=["Actions"])
app.include_router(cost.router, prefix="/api/cost", tags=["Cost"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"])
