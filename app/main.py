import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.routers import disasters
from app.modules.disaster_scanner.broadcaster import stream_consumer_worker

background_tasks = set()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(level=logging.INFO)
    logger.info("Starting FastAPI Lifespan...")

    task = asyncio.create_task(stream_consumer_worker())
    background_tasks.add(task)

    yield

    logger.info("Shutting down FastAPI...")
    task.cancel()


app = FastAPI(
    title="Disaster Adviser API",
    version="1.0.0",
    contact={
        "name": "Disaster Adviser Team",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

from app.api.routers import auth, calendar, user, oauth

app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(calendar.router)
app.include_router(user.router)
app.include_router(disasters.router, tags=["Disasters"])