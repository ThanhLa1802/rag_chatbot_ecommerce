# app/worker.py
from celery import Celery
from app.services.sync_service import sync_product_to_vector_db

# Docker service name: redis, Local development: localhost
REDIS_URL = "redis://redis:6379/0"

celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

@celery_app.task(bind=True, max_retries=3)  # Tự động thử lại nếu lỗi mạng
def task_sync_to_qdrant(self, product_id, name, description, category, price):
    """Sync product to Qdrant vector database asynchronously."""
    try:
        sync_product_to_vector_db(
            product_id=product_id,
            name=name,
            description=description,
            category=category,
            price=price
        )
    except Exception as exc:
        # Nếu Qdrant lỗi, thử lại sau 5 phút
        raise self.retry(exc=exc, countdown=300)