from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .db import init_db
from .routers import ingestion, monitor, export, ui, test_celery, api, hybrid_sync, manual_input
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="AI-CLAIM Data Hub", lifespan=lifespan)

# CORS middleware untuk iframe embedding dari web service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include all routers
app.include_router(ingestion.router, prefix="/ingestion", tags=["Ingestion"])
app.include_router(monitor.router, prefix="/monitor", tags=["Monitor"])
app.include_router(export.router, prefix="/export", tags=["Export"])
app.include_router(ui.router, tags=["Dashboard"])
app.include_router(test_celery.router, tags=["Testing"])
app.include_router(api.router)  # FASE 1.3: API for Web AI Claim
app.include_router(hybrid_sync.router)  # Hybrid Sync Router
app.include_router(manual_input.router)  # ✨ NEW: Manual Input Router

# app.include_router(monitoring.router, prefix="/api", tags=["monitoring"])