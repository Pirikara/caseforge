from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api import projects
from app.logging_config import logger
from app.config import settings
from app.models import init_db

app = FastAPI(title=settings.APP_NAME)

# アプリケーション起動時にデータベースを初期化
@app.on_event("startup")
def on_startup():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")

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