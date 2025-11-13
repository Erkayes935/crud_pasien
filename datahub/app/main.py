from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .db import init_db
from .routers import ingestion, monitor, export, ui, test_celery, api
from fastapi.staticfiles import StaticFiles
#from app.routers import monitoring

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="AI-CLAIM Data Hub", lifespan=lifespan)

# Enable CORS to allow iframe embedding from Web app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for iframe embedding
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(ingestion.router, prefix="/ingestion", tags=["Ingestion"])
app.include_router(monitor.router, prefix="/monitor", tags=["Monitor"])
app.include_router(export.router, prefix="/export", tags=["Export"])
app.include_router(ui.router, tags=["Dashboard"])
app.include_router(test_celery.router, tags=["Testing"])
app.include_router(api.router)  # FASE 1.3: API for Web AI Claim
#app.include_router(monitoring.router, prefix="/api", tags=["monitoring"])