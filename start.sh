#!/bin/bash

# Exit on error
set -e

# Print each command
set -x

# Install dependencies
pip install -r requirements.txt

# Make sure uvicorn is installed
pip install "uvicorn[standard]"

# Set default port if not set
export PORT="${PORT:-3000}"

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port "$PORT" --log-level debug 