from celery import Celery
from capital_group.configs import config

def make_celery(app_name=__name__):
    """
    Factory function to create and configure a Celery instance.
    This setup ensures that the Celery task context has access to 
    app configurations and shared resources.
    """
    
    celery_instance = Celery(
        app_name,
        broker=config.CELERY_BROKER_URL,
        backend=config.CELERY_RESULT_BACKEND,
        include=['capital_group.celery.tasks']  # Tells Celery where to find tasks
    )

    # Optimization: Update Celery configuration with best practices
    celery_instance.conf.update(
        task_serializer='json',
        accept_content=['json'],  # Security: only accept JSON
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        # Performance: Pre-fetch 1 task at a time to prevent one worker 
        # from hogging long-running tasks while others are idle.
        worker_prefetch_multiplier=1,
        # Ensure tasks are only acknowledged after they are finished
        task_acks_late=True,
    )

    return celery_instance

# Global instance to be used by the celery_worker.py entrypoint
celery_app = make_celery(config.PROJECT_NAME)