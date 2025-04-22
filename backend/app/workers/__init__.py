from celery import Celery
import os
from dotenv import load_dotenv
from app.config import settings

load_dotenv()

celery_app = Celery(
    "caseforge",
    broker=settings.REDIS_URL,
)

# タスク検出パスを追加
celery_app.autodiscover_tasks(["app.workers"])
