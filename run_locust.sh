#!/bin/bash
# Script to run Locust load test with CSV/HTML export

# Configuration
HOST="${LOCUST_HOST:-http://localhost:8000}"  # Default host, override with LOCUST_HOST env var
USERS="${LOCUST_USERS:-200}"  # Number of concurrent users (targeting ~200 RPS)
SPAWN_RATE="${LOCUST_SPAWN_RATE:-50}"  # Users to spawn per second
RUN_TIME="${LOCUST_RUN_TIME:-5m}"  # Test duration
CSV_PREFIX="${LOCUST_CSV_PREFIX:-locust_stats}"
HTML_REPORT="${LOCUST_HTML_REPORT:-locust_report.html}"

echo "=========================================="
echo "Locust Load Test Configuration"
echo "=========================================="
echo "Target Host: $HOST"
echo "Concurrent Users: $USERS"
echo "Spawn Rate: $SPAWN_RATE users/second"
echo "Test Duration: $RUN_TIME"
echo "CSV Prefix: $CSV_PREFIX"
echo "HTML Report: $HTML_REPORT"
echo "=========================================="
echo ""

# Check if test PDF exists, create if not
if [ ! -f "test_document.pdf" ]; then
    echo "Creating test PDF..."
    python3 create_test_pdf.py
fi

# Run Locust in headless mode with CSV/HTML export
locust \
    --headless \
    --host "$HOST" \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$RUN_TIME" \
    --csv "$CSV_PREFIX" \
    --html "$HTML_REPORT" \
    --loglevel INFO \
    --locustfile locustfile.py

echo ""
echo "=========================================="
echo "Test completed!"
echo "=========================================="
echo "CSV files generated:"
echo "  - ${CSV_PREFIX}_stats.csv"
echo "  - ${CSV_PREFIX}_stats_history.csv"
echo "  - ${CSV_PREFIX}_failures.csv"
echo "HTML report: $HTML_REPORT"
echo "=========================================="
