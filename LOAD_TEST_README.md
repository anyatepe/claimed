# Load Testing for Summarization API

This directory contains Locust load testing scripts to simulate concurrent requests to the `/v1/summarize` endpoint.

## Files

- `locustfile.py` - Main Locust test script that simulates users making summarization requests
- `run_load_test.sh` - Bash script to run the load test with predefined parameters
- `generate_metrics_report.py` - Python script to generate a human-readable metrics report from Locust CSV output
- `requirements.txt` - Python dependencies (Locust)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Option 1: Using the shell script (recommended)

```bash
# Run with default settings (500 users, 5 minutes)
./run_load_test.sh

# Or customize via environment variables:
HOST=http://localhost:8000 USERS=500 SPAWN_RATE=50 DURATION=5m ./run_load_test.sh
```

### Option 2: Using Locust directly

#### Headless mode (no UI):
```bash
locust --headless --host=http://localhost:8000 --users=500 --spawn-rate=50 --run-time=5m
```

#### Web UI mode:
```bash
locust --host=http://localhost:8000
```
Then open http://localhost:8089 in your browser to configure and start the test.

### Generate Metrics Report

After running the load test, generate a detailed metrics report:

```bash
python generate_metrics_report.py
```

Or specify custom paths:
```bash
python generate_metrics_report.py reports/stats_stats.csv metrics_report.txt
```

## Configuration

The test script (`locustfile.py`) can be customized:

- **Concurrent users**: Set via `--users` parameter (default: 500)
- **Spawn rate**: Users spawned per second via `--spawn-rate` (default: 50)
- **Test duration**: Set via `--run-time` (e.g., `5m`, `10m`, `1h`)
- **Wait time**: Time between requests per user (currently 1-3 seconds, configurable in `locustfile.py`)
- **Text length**: Random text generation between 50-500 words (configurable in `generate_random_text()`)

## Output

The load test generates:

1. **HTML Report**: `reports/report.html` - Interactive web-based report
2. **CSV Stats**: `reports/stats_stats.csv` - Detailed statistics in CSV format
3. **Failures CSV**: `reports/stats_failures.csv` - List of failed requests
4. **Metrics Report**: `metrics_report.txt` - Human-readable summary (after running `generate_metrics_report.py`)

## Metrics Tracked

- **Latency**: Min, Average, Median, Max, and percentiles (P50, P66, P75, P80, P90, P95, P98, P99, P100)
- **Throughput**: Requests per second (RPS)
- **Success Rate**: Percentage of successful requests
- **Failure Count**: Number of failed requests

## Example Output

```
OVERALL STATISTICS
------------------------------------------------------------
Total Requests:        12,450
Failed Requests:       23
Success Rate:          99.82%
Requests per Second:   41.50 RPS

RESPONSE TIME STATISTICS (milliseconds)
------------------------------------------------------------
Minimum:               45.23 ms
Average:               234.56 ms
Median (P50):          198.34 ms
Maximum:               1,234.56 ms
```
