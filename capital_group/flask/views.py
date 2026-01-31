from flask import Blueprint, jsonify, request
from capital_group.celery.tasks import scraping_task, extraction_task
from capital_group.Utils.ce_logger import get_logger
import os

# module-level logger
logger = get_logger(__name__)

# Initialize the blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health Check Endpoint
    ---
    responses:
      200:
        description: Returns status 'UP' if the service is running.
    """
    return jsonify({"status": "UP", "message": "Service is healthy"}), 200

@main_bp.route('/scrape', methods=['POST'])
def trigger_scraping():
    """Trigger a Scraping Task

    ---
    tags:
      - Scraping
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            url:
              type: string
              description: Page or direct file URL to download from
            dest_path:
              type: string
              description: Local folder where downloaded file should be stored (required)
            
            chromedriver_path:
              type: string
              description: Filesystem path to chromedriver executable (required for local driver use)
          example:
            url: "http://localhost:8000/large_sample_data.xlsx"
            dest_path: "C:/Users/RAVI KUMAR/OneDrive/Desktop/capiq2"
            chromedriver_path: "C:/Users/RAVI KUMAR/OneDrive/Desktop/capiq2/ETL_Project_Final_phase/chromedriver.exe"
          required:
            - url
            - dest_path
            - chromedriver_path
            
    responses:
      202:
        description: Task queued successfully; returns task id
        schema:
          type: object
          properties:
            task_id:
              type: string
            status:
              type: string
      200:
        description: Synchronous download completed
        schema:
          type: object
          properties:
            status:
              type: string
            downloaded:
              type: string
      400:
        description: Missing or invalid input
        schema:
          type: object
          properties:
            error:
              type: string

    """
    data = request.get_json() or {}
    url = data.get('url')
    dest_path = data.get('dest_path')
    
    chromedriver_path = data.get('chromedriver_path')
    
    # Basic validation: require url, dest_path, and chromedriver_path
    if not url or not dest_path or not chromedriver_path:
        return jsonify({"error": "Fields 'url', 'dest_path', and 'chromedriver_path' are required"}), 400

    # Ensure chromedriver path exists
    if not os.path.exists(chromedriver_path):
        return jsonify({"error": f"chromedriver_path does not exist: {chromedriver_path}"}), 400

    # Ensure dest_path directory exists (create it)
    try:
        os.makedirs(dest_path, exist_ok=True)
    except Exception as e:
        return jsonify({"error": f"Failed to create dest_path: {e}"}), 400

    # If requested, run synchronously (blocks until download completes)
    

    # Otherwise trigger the Celery task asynchronously; include dest_path and headless flag
    task = scraping_task.delay(url, dest_path, chromedriver_path)

    logger.info(f"Scraping task queued with ID: {task.id}")
    return jsonify({
        "task_id": task.id,
        "status": "Task Queued"
    }), 202

@main_bp.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """
    Check Task Status
    ---
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Returns the current status of the background task.
    """
    from capital_group.celery.celery_app import celery_app
    res = celery_app.AsyncResult(task_id)
    
    return jsonify({
        "task_id": task_id,
        "state": res.state,
        "result": res.result if res.ready() else None
    }), 200

