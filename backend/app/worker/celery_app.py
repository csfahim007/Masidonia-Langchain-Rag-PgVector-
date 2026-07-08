import logging

from app.core.config import config

logger = logging.getLogger(__name__)

if config.CELERY_ENABLED:
    from celery import Celery

    celery_app = Celery(
        "masidonia",
        broker=config.CELERY_BROKER_URL,
        backend=config.CELERY_BROKER_URL,
    )
    celery_app.conf.task_serializer = "json"
    celery_app.conf.result_serializer = "json"
    celery_app.conf.accept_content = ["json"]
else:
    celery_app = None
