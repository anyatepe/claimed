# Locust Load Test for Document Upload and Query API

This Locustfile tests the document upload and query API endpoints:
- `/v1/documents` - Upload PDF documents
- `/v1/chat/query` - Query uploaded documents

## Target Performance
- **Sustain 200 RPS** (requests per second)
- **p95 latency < 1.8s** (95th percentile response time)
- **Streaming disabled** for queries

## Setup

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

2. Create test PDF (if not already created):
```bash
python3 create_test_pdf.py
```

## Running the Test

### Option 1: Using the run script (recommended)
```bash
# Set target host (default: http://localhost:8000)
export LOCUST_HOST=http://your-api-host:port

# Run with default settings (200 users, 5 minutes)
./run_locust.sh

# Or customize:
export LOCUST_USERS=200
export LOCUST_SPAWN_RATE=50
export LOCUST_RUN_TIME=10m
./run_locust.sh
```

### Option 2: Direct Locust command
```bash
# Headless mode with CSV/HTML export
locust --headless \
    --host http://your-api-host:port \
    --users 200 \
    --spawn-rate 50 \
    --run-time 5m \
    --csv locust_stats \
    --html locust_report.html \
    --locustfile locustfile.py
```

### Option 3: Web UI mode (for interactive testing)
```bash
locust --host http://your-api-host:port --locustfile locustfile.py
# Then open http://localhost:8089 in your browser
```

## Output Files

After running the test, you'll get:

- **CSV Files:**
  - `locust_stats_stats.csv` - Overall statistics
  - `locust_stats_stats_history.csv` - Time-series statistics
  - `locust_stats_failures.csv` - Failure details

- **HTML Report:**
  - `locust_report.html` - Interactive HTML report with charts and statistics

## Configuration

### Adjusting for 200 RPS Target

To achieve 200 RPS, you may need to adjust:

1. **Number of users**: Start with 200 concurrent users, adjust based on actual RPS achieved
   ```bash
   export LOCUST_USERS=200  # Increase if RPS is too low
   ```

2. **Spawn rate**: How quickly users are added
   ```bash
   export LOCUST_SPAWN_RATE=50  # Users per second
   ```

3. **Wait time**: In `locustfile.py`, the `wait_time` controls delay between tasks
   - Current: `between(0.1, 0.5)` seconds
   - Lower values = higher RPS

### Task Weights

The Locustfile uses task weights:
- Query task: weight 3 (runs 3x more often)
- Upload task: weight 1

This simulates a realistic workload where queries are more frequent than uploads.

## API Payload Structure

The Locustfile assumes the following API structure. If your API differs, modify the payloads in `locustfile.py`:

### Document Upload (`/v1/documents`)
- Method: POST
- Content-Type: multipart/form-data
- Field name: `file`
- Expected response: JSON with `id` or `document_id` field

### Query (`/v1/chat/query`)
- Method: POST
- Content-Type: application/json
- Payload:
  ```json
  {
    "question": "string",
    "document_id": "string",
    "stream": false
  }
  ```

## Monitoring Performance

Check the generated CSV files or HTML report for:
- **RPS**: Requests per second (should sustain ~200)
- **p95**: 95th percentile response time (should be < 1.8s)
- **Failures**: Error rate and failure reasons
- **Response times**: Min, max, median, p95, p99

## Troubleshooting

1. **Low RPS**: Increase `LOCUST_USERS` or decrease `wait_time` in locustfile.py
2. **High p95**: Check API performance, network latency, or reduce load
3. **Connection errors**: Verify `LOCUST_HOST` is correct and API is accessible
4. **Document ID not found**: Check API response structure and update `upload_document()` method

## Notes

- Uses `FastHttpUser` for better performance at high RPS
- Each user uploads one document and queries it multiple times
- Random questions are selected from a predefined list
- Streaming is explicitly disabled (`stream: false`)
