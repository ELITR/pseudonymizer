#!/bin/bash

# Run config
export FLASK_APP=psan 
export FLASK_RUN_HOST=0.0.0.0

# Use venv
source venv/bin/activate

# Start background worker
(celery -A psan.celery worker)&
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start celery worker. EXIT $status" >&2
  exit $status
fi

# Start web
(flask run)&
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start flask. EXIT $status" >&2
  exit $status
fi

# Naive check runs checks once a minute to see if either of the processes exited.
# This illustrates part of the heavy lifting you need to do if you want to run
# more than one service in a container. The container exits with an error
# if it detects that either of the processes has exited.
# Otherwise it loops forever, waking up every 60 seconds

while sleep 60; do
  ps aux | grep flask | grep -q -v grep
  PROCESS_1_STATUS=$?
  ps aux | grep celery | grep -q -v grep
  PROCESS_2_STATUS=$?
  # If the greps above find anything, they exit with 0 status
  # If they are not both 0, then something is wrong
  if [ $PROCESS_1_STATUS -ne 0 -o $PROCESS_2_STATUS -ne 0 ]; then
    echo "One of the processes has already exited." >&2
    exit 1
  fi
done