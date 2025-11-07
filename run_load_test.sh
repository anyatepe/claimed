#!/bin/bash
# Script to run Locust load test and generate metrics report

# Default values
HOST="${HOST:-http://localhost:8000}"
USERS="${USERS:-500}"
SPAWN_RATE="${SPAWN_RATE:-50}"
DURATION="${DURATION:-5m}"
REPORT_DIR="${REPORT_DIR:-./reports}"

echo "Starting Locust load test..."
echo "Target host: $HOST"
echo "Concurrent users: $USERS"
echo "Spawn rate: $SPAWN_RATE users/second"
echo "Test duration: $DURATION"
echo ""

# Create reports directory if it doesn't exist
mkdir -p "$REPORT_DIR"

# Run Locust in headless mode
locust \
    --headless \
    --host="$HOST" \
    --users="$USERS" \
    --spawn-rate="$SPAWN_RATE" \
    --run-time="$DURATION" \
    --html="$REPORT_DIR/report.html" \
    --csv="$REPORT_DIR/stats" \
    --loglevel INFO

echo ""
echo "Load test completed!"
echo "Reports generated in: $REPORT_DIR"
echo "  - HTML report: $REPORT_DIR/report.html"
echo "  - CSV stats: $REPORT_DIR/stats_stats.csv"
echo "  - Failures: $REPORT_DIR/stats_failures.csv"
echo ""
echo "To view the HTML report, open: $REPORT_DIR/report.html"
