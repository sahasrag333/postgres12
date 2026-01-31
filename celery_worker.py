# from capital_group.celery.celery_app import celery_app
# from capital_group.flask.factory import create_app

# # Create a Flask app instance to ensure the Celery worker 
# # has access to the Flask application context if needed
# flask_app = create_app()
# flask_app.app_context().push()

# # The 'celery_app' instance is what the worker -A flag will look for
# app = celery_app

# if __name__ == '__main__':
#     # This allows running 'python celery_worker.py' for basic debugging,
#     # though usually, you'd run it via the celery command.
#     celery_app.start()

from capital_group.flask.factory import create_app
from capital_group.celery.celery_app import celery_app
from capital_group.Utils.ce_logger import get_logger, SessionLocal, ScrapedResult
from capital_group.Utils.selenium_web_extraction import download_file_from_url
logger = get_logger(__name__)

flask_app = create_app()
flask_app.app_context().push()
app = celery_app

@app.task(name="scraping_task") # Use the name you currently have
def scraping_task(url, dest_path: str = None, headless: bool = True, chromedriver_path: str = None):
    logger.info(f"Worker processing: {url}")

    downloaded_path = None
    if dest_path:
        logger.info(f"Attempting to download to: {dest_path}")
        downloaded_path = download_file_from_url(url, download_dir=dest_path, headless=headless, chromedriver_path=chromedriver_path)
        logger.info(f"Download result: {downloaded_path}")

    # 1. Simulate the data found (include downloaded path if available)
    extracted_data = {
        "url": url,
        "title": "Sample Title",
        "content": "Sample content from the page",
        "downloaded_path": downloaded_path,
    }

    # 2. Save to Database
    db = SessionLocal()
    try:
        new_record = ScrapedResult(url=url, data=extracted_data)
        db.add(new_record)
        db.commit()
        logger.info("Data saved to SQLite successfully.")
    except Exception as e:
        logger.error(f"Failed to save to DB: {e}")
    finally:
        db.close()

    return extracted_data