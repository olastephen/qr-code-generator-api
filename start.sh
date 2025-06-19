#!/bin/bash

# Exit on error
set -e

# Define log directory - use /tmp as fallback if /data is not writable
if [ -w "/data" ]; then
    LOG_DIR="/data/logs"
else
    LOG_DIR="/tmp/logs"
fi

# Create and set permissions for logs directory
mkdir -p $LOG_DIR
chmod -R 777 $LOG_DIR

# Export log directory for the application
export APP_LOG_DIR=$LOG_DIR

# Install dependencies
pip install --no-cache-dir -r requirements.txt

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port 3000 --log-level debug --log-file $LOG_DIR/app.log 