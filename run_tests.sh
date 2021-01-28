#!/bin/bash

# Run config
export FLASK_APP=psan 
export FLASK_RUN_HOST=0.0.0.0

# Use venv
source venv/bin/activate

# Start background worker
(celery -A psan.celery.celery worker > /dev/null)&
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start celery worker. EXIT $status" >&2
  exit $status
fi

pytest