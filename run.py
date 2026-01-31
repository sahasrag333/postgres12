from capital_group.flask.factory import create_app
from capital_group.configs import config
import os
import socket
import subprocess
from capital_group.Utils.ce_logger import get_logger

logger = get_logger()

# Create the Flask instance
app = create_app()

# if __name__ == "__main__":
#     logger.info(f"Starting {config.PROJECT_NAME} in {config.FLASK_ENV} mode...")
    
#     # We set host to 0.0.0.0 so it is accessible inside Docker/K8s
#     app.run(
#         host="0.0.0.0", 
#         port=5000, 
#         debug=config.DEBUG
#     )

def is_port_in_use(port):
    # Use the module 'socket' to access constants like AF_INET
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

if __name__ == "__main__":
    # Ensure FLASK_ENV is checked safely
    is_dev = os.getenv('FLASK_ENV') == 'development' or os.getenv('DEBUG') == 'True'
    
    if is_dev and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        if not is_port_in_use(5555):
            logger.info("Starting Flower monitor on http://localhost:5555")
            # Using 'python -m celery' is more reliable on Windows
            subprocess.Popen(['python', '-m', 'celery', '-A', 'celery_worker.app', 'flower', '--port=5555'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            logger.info("Flower is already running on port 5555.")

    logger.info("Starting Flask API on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)