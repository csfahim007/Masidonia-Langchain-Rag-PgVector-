import importlib
import logging

logger = logging.getLogger(__name__)

try:
    from app.worker.celery_app import celery_app

    if celery_app:

        @celery_app.task(name="app.worker.tasks.run_callable")
        def run_callable(module_name: str, func_name: str, args: tuple, kwargs: dict):
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            return func(*args, **kwargs)

except ImportError:
    logger.info("Celery not configured")
