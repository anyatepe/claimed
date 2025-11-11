# End-to-End Quickstart Guide

This guide will walk you through setting up and using the FastAPI application from scratch, including ingesting a PDF document, querying the chat interface, and viewing citations.

## Prerequisites

- Docker and Docker Compose installed
- A sample PDF file for testing (or use the provided sample)

## Step 1: Start the Application

Start all services using Docker Compose:

```bash
make run
```

Or manually:

```bash
docker-compose up -d
```

This will start:
- FastAPI application server
- Vector database (e.g., Qdrant, Chroma, or Pinecone)
- Optional: Database for document metadata
- Optional: Redis for caching

Wait for all services to be healthy. You can check the status with:

```bash
docker-compose ps
```

## Step 2: Verify the API is Running

Open your browser and navigate to:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

You should see the Swagger UI with all available endpoints.

## Step 3: Ingest a Sample PDF

### Option A: Using the Web UI (Swagger)

1. Navigate to http://localhost:8000/docs
2. Find the `POST /api/v1/documents/ingest` endpoint
3. Click "Try it out"
4. Click "Choose File" and select your PDF
5. Click "Execute"
6. Note the `document_id` from the response

### Option B: Using cURL

```bash
curl -X POST "http://localhost:8000/api/v1/documents/ingest" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/sample.pdf"
```

### Option C: Using Python

```python
import requests

url = "http://localhost:8000/api/v1/documents/ingest"
files = {'file': open('sample.pdf', 'rb')}
response = requests.post(url, files=files)
print(response.json())
```

**Expected Response:**
```json
{
  "document_id": "doc_123456789",
  "filename": "sample.pdf",
  "status": "processing",
  "message": "Document uploaded successfully"
}
```

Wait a few moments for processing to complete. Check status with:

```bash
curl http://localhost:8000/api/v1/documents/doc_123456789
```

## Step 4: Query the Chat Interface

Once the document is processed, you can query it.

### Option A: Using the Web UI (Swagger)

1. Navigate to http://localhost:8000/docs
2. Find the `POST /api/v1/chat/query` endpoint
3. Click "Try it out"
4. Enter your query in the request body:
   ```json
   {
     "query": "What are the main points discussed in the document?",
     "max_results": 5
   }
   ```
5. Click "Execute"
6. View the response with answer and citations

### Option B: Using cURL

```bash
curl -X POST "http://localhost:8000/api/v1/chat/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main points discussed in the document?",
    "max_results": 5
  }'
```

### Option C: Using Python

```python
import requests

url = "http://localhost:8000/api/v1/chat/query"
payload = {
    "query": "What are the main points discussed in the document?",
    "max_results": 5
}
response = requests.post(url, json=payload)
print(response.json())
```

**Expected Response:**
```json
{
  "query_id": "query_987654321",
  "query": "What are the main points discussed in the document?",
  "answer": "The document discusses several key points including...",
  "citations": [
    {
      "document_id": "doc_123456789",
      "document_name": "sample.pdf",
      "page": 1,
      "excerpt": "The main topic is...",
      "relevance_score": 0.95
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Step 5: View Citations

Citations are included in the query response, but you can also retrieve them separately.

### Option A: Using the Web UI

1. Navigate to http://localhost:8000/docs
2. Find the `GET /api/v1/citations/{query_id}` endpoint
3. Click "Try it out"
4. Enter the `query_id` from Step 4
5. Click "Execute"

### Option B: Using cURL

```bash
curl "http://localhost:8000/api/v1/citations/query_987654321"
```

### Option C: Using Python

```python
import requests

query_id = "query_987654321"
url = f"http://localhost:8000/api/v1/citations/{query_id}"
response = requests.get(url)
print(response.json())
```

**Expected Response:**
```json
{
  "query_id": "query_987654321",
  "citations": [
    {
      "document_id": "doc_123456789",
      "document_name": "sample.pdf",
      "page": 1,
      "excerpt": "The main topic is...",
      "relevance_score": 0.95,
      "start_char": 100,
      "end_char": 250
    },
    {
      "document_id": "doc_123456789",
      "document_name": "sample.pdf",
      "page": 2,
      "excerpt": "Another important point...",
      "relevance_score": 0.87,
      "start_char": 50,
      "end_char": 200
    }
  ]
}
```

## Step 6: List All Documents

View all ingested documents:

```bash
curl http://localhost:8000/api/v1/documents
```

## Step 7: Clean Up (Optional)

To stop all services:

```bash
make stop
```

Or manually:

```bash
docker-compose down
```

To remove all data (volumes):

```bash
docker-compose down -v
```

## Troubleshooting

### Service Not Starting

```bash
# Check logs
docker-compose logs

# Check specific service logs
docker-compose logs api
docker-compose logs vector-db
```

### Document Not Processing

1. Check document processing status:
   ```bash
   curl http://localhost:8000/api/v1/documents/{document_id}
   ```

2. Check API logs for errors:
   ```bash
   docker-compose logs api | tail -50
   ```

### Query Returns No Results

1. Ensure the document has finished processing
2. Try a simpler query
3. Check that the vector database is running:
   ```bash
   docker-compose ps vector-db
   ```

### Port Already in Use

If port 8000 is already in use, modify `docker-compose.yml` to use a different port:

```yaml
services:
  api:
    ports:
      - "8001:8000"  # Change 8001 to your preferred port
```

## Next Steps

- Read the [Environment Variables Reference](environment.md) for configuration options
- Explore the [OpenAPI Documentation](openapi.md) for detailed API information
- Review the [Security Model](environment.md#security-model) for production deployment

## Example Workflow Script

Here's a complete example script that automates the quickstart:

```bash
#!/bin/bash

# Start services
echo "Starting services..."
make run

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Ingest a PDF
echo "Ingesting PDF..."
DOC_ID=$(curl -s -X POST "http://localhost:8000/api/v1/documents/ingest" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.pdf" | jq -r '.document_id')

echo "Document ID: $DOC_ID"

# Wait for processing
echo "Waiting for document processing..."
sleep 15

# Query the document
echo "Querying document..."
curl -X POST "http://localhost:8000/api/v1/chat/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize the main points", "max_results": 3}' | jq

echo "Quickstart complete!"
```
