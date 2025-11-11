#!/bin/bash
# Script to run smoke tests for metrics

set -e

echo "Starting application in background..."
python app.py &
APP_PID=$!

# Wait for app to start
echo "Waiting for application to start..."
sleep 3

# Check if app is running
if ! kill -0 $APP_PID 2>/dev/null; then
    echo "Application failed to start"
    exit 1
fi

echo "Running smoke tests..."
pytest test_metrics.py -v

# Cleanup
echo "Stopping application..."
kill $APP_PID 2>/dev/null || true

echo "Tests completed!"
