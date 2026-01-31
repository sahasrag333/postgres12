#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting Application in Mode: $TYPE"

if [ "$TYPE" == "FLASK" ]; then
    # Run Flask via Gunicorn for production
    echo "Launching Flask Web Server..."
    exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 run:app

elif [ "$TYPE" == "CELERY_WORKER" ]; then
    # Run the Celery Worker
    # -n sets a unique name for the node based on the hostname
    echo "Launching Celery Worker..."
    exec celery -A celery_worker.app worker --loglevel=info -n worker@%h

elif [ "$TYPE" == "FLOWER" ]; then
    # Run Flower for monitoring Celery tasks
    echo "Launching Celery Flower Monitor..."
    exec celery -A celery_worker.app flower --port=5555

else
    echo "ERROR: TYPE environment variable not set or invalid (Expected: FLASK, CELERY_WORKER, or FLOWER)"
    exit 1
fi