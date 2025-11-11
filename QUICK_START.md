# Quick Start Guide

## Run the Load Test

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Set your API host
export LOCUST_HOST=http://your-api-host:port

# 3. Run the test
./run_locust.sh
```

## Files Created

- `locustfile.py` - Main Locust test file
- `test_document.pdf` - Small PDF for testing (2KB)
- `run_locust.sh` - Convenience script to run tests
- `requirements.txt` - Python dependencies
- `LOCUST_README.md` - Detailed documentation

## Output

After running, you'll get:
- `locust_stats_stats.csv` - Overall statistics
- `locust_stats_stats_history.csv` - Time-series data
- `locust_stats_failures.csv` - Failure details
- `locust_report.html` - Interactive HTML report

## Target Metrics

- **200 RPS** sustained
- **p95 < 1.8s** response time
- Streaming disabled

## Adjusting Load

To achieve 200 RPS, adjust:
- `LOCUST_USERS` - Number of concurrent users (start with 200)
- `LOCUST_SPAWN_RATE` - Users spawned per second (start with 50)
- `wait_time` in `locustfile.py` - Delay between tasks (currently 0.1-0.5s)
