"""
Celery App Configuration untuk AI-CLAIM Data Hub
Digunakan untuk async processing (AI analysis, batch operations)
"""
from celery import Celery
import os

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app
celery_app = Celery(
    "ai_claim_datahub",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.ai_tasks"]  # Import tasks module
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Optional: Task routes for different queues
celery_app.conf.task_routes = {
    "app.tasks.ai_tasks.process_ai_analysis": {"queue": "ai_processing"},
    "app.tasks.ai_tasks.batch_process": {"queue": "batch_operations"},
}

if __name__ == "__main__":
    celery_app.start()
