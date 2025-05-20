from celery import Celery
import os
from dotenv import load_dotenv
from app.config import settings

load_dotenv()

celery_app = Celery(
    "caseforge",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.autodiscover_tasks(["app.workers"])
