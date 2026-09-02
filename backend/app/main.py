from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import db
from app.core.config import settings
from app.core.security import auth_middleware
from app.api import health, projects, inspections, permits, disputes, audit


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.pool = await db.create_pool()
    try:
        yield
    finally:
        await db.close_pool()


app = FastAPI(
    title="NoblePort API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [settings.supabase_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware
app.middleware("http")(auth_middleware)

# Routers
app.include_router(health.router)
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(inspections.router, prefix="/inspections", tags=["inspections"])
app.include_router(permits.router, prefix="/permits", tags=["permits"])
app.include_router(disputes.router, prefix="/disputes", tags=["disputes"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])
