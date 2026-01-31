from capital_group.celery.celery_app import celery_app
from capital_group.Utils.ce_logger import logger

def start_worker():
    """
    Main entry point for starting the Celery worker via Python.
    This can be used for custom initialization before the worker starts.
    """
    try:
        logger.info("Initializing Celery Worker...")
        
        # This is where you would put logic that needs to run 
        # ONCE when the worker process starts (e.g., pre-downloading ML models)
        
        celery_app.start()
    except Exception as e:
        logger.critical(f"Failed to start Celery worker: {e}")
        raise

if __name__ == "__main__":
    start_worker()