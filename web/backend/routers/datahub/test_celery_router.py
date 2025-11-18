"""
Test Celery Router
Endpoint untuk testing Celery & Redis connection
"""
from fastapi import APIRouter
from backend.tasks.ai_tasks import test_task
from celery.result import AsyncResult
from backend.celery_app import celery_app

router = APIRouter()

@router.post("/test/celery")
def test_celery_task():
    """
    Test Celery dengan mengirim task sederhana
    """
    # Kirim task ke Celery worker
    task = test_task.delay("Hello from Data Hub!")
    
    return {
        "status": "task_queued",
        "task_id": task.id,
        "message": "Task berhasil dikirim ke Celery worker. Cek /test/celery/result/{task_id}"
    }

@router.get("/test/celery/result/{task_id}")
def get_task_result(task_id: str):
    """
    Cek hasil task Celery
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.ready():
        if task_result.successful():
            return {
                "status": "completed",
                "task_id": task_id,
                "result": task_result.result
            }
        else:
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(task_result.result)
            }
    else:
        return {
            "status": "processing",
            "task_id": task_id,
            "state": task_result.state
        }

@router.get("/test/celery/inspect")
def inspect_celery():
    """
    Inspect Celery workers status
    """
    inspect = celery_app.control.inspect()
    
    return {
        "active_tasks": inspect.active(),
        "scheduled_tasks": inspect.scheduled(),
        "registered_tasks": inspect.registered(),
        "stats": inspect.stats()
    }
