from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api import projects
from app.logging_config import logger
from app.config import settings
from app.models import init_db

# lifespan イベントハンドラ
@asynccontextmanager
async def lifespan(app: FastAPI):
    # アプリケーション起動時
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
    yield
    # アプリケーション終了時
    logger.info("Shutting down...")

import debugpy

debugpy.listen(("0.0.0.0", 4444))  # ポートは好きに（デフォ5678）
print("⚡ debugpy waiting for attach...")

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)

@app.get("/health")
def health():
    logger.debug("Health check endpoint called")
    return {"status": "ok"}

logger.info(f"Application {settings.APP_NAME} started")