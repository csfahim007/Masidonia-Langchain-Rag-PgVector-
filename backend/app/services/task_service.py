import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from app.core.config import config

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


class TaskService:
    """Background task queue. Uses Celery when enabled, otherwise in-process executor."""

    @staticmethod
    def enqueue(name: str, func: Callable, *args, **kwargs) -> None:
        if config.CELERY_ENABLED:
            TaskService._enqueue_celery(name, func, *args, **kwargs)
        else:
            TaskService._enqueue_local(name, func, *args, **kwargs)

    @staticmethod
    def _enqueue_local(name: str, func: Callable, *args, **kwargs) -> None:
        def _run():
            try:
                func(*args, **kwargs)
            except Exception as exc:
                logger.exception("Background task %s failed: %s", name, exc)

        _executor.submit(_run)
        logger.info("Queued background task (local): %s", name)

    @staticmethod
    def _enqueue_celery(name: str, func: Callable, *args, **kwargs) -> None:
        try:
            from app.worker.celery_app import celery_app

            celery_app.send_task(
                "app.worker.tasks.run_callable",
                args=[func.__module__, func.__name__, args, kwargs],
            )
            logger.info("Queued background task (celery): %s", name)
        except Exception as exc:
            logger.warning("Celery unavailable, falling back to local executor: %s", exc)
            TaskService._enqueue_local(name, func, *args, **kwargs)
