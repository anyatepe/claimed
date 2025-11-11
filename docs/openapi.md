# OpenAPI Documentation

FastAPI automatically generates interactive API documentation using OpenAPI (formerly Swagger) and ReDoc standards. This documentation is available when the application is running.

## Accessing the Documentation

Once the FastAPI application is running, you can access the API documentation at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON Schema**: `http://localhost:8000/openapi.json`

## Swagger UI

The Swagger UI (`/docs`) provides an interactive interface where you can:

- Browse all available API endpoints
- View request/response schemas
- Test API endpoints directly from the browser
- See example requests and responses
- Authenticate and make live API calls

### Using Swagger UI

1. Navigate to `http://localhost:8000/docs` in your browser
2. Expand any endpoint to see its details
3. Click "Try it out" to test an endpoint
4. Fill in the required parameters
5. Click "Execute" to send the request
6. View the response below

## ReDoc

ReDoc (`/redoc`) provides an alternative documentation interface with:

- Clean, readable documentation layout
- Better for reading and understanding the API
- Search functionality
- Responsive design

## OpenAPI JSON Schema

The OpenAPI JSON schema (`/openapi.json`) provides the raw OpenAPI specification that can be:

- Imported into API testing tools (Postman, Insomnia, etc.)
- Used for code generation
- Integrated with API gateways
- Shared with frontend developers

## API Endpoints

The FastAPI application typically includes the following endpoints:

### Document Ingestion

- **POST `/api/v1/documents/ingest`**: Upload and ingest a PDF document
  - Accepts multipart/form-data with a PDF file
  - Returns document ID and processing status

### Chat/Query

- **POST `/api/v1/chat/query`**: Query the document knowledge base
  - Accepts a query string and optional parameters
  - Returns a response with citations

- **GET `/api/v1/chat/history`**: Retrieve chat history
  - Returns list of previous queries and responses

### Document Management

- **GET `/api/v1/documents`**: List all ingested documents
- **GET `/api/v1/documents/{document_id}`**: Get document details
- **DELETE `/api/v1/documents/{document_id}`**: Delete a document

### Citations

- **GET `/api/v1/citations/{query_id}`**: Get citations for a specific query
  - Returns source documents and relevant excerpts

## Authentication

If authentication is enabled, you'll need to:

1. Obtain an API key or token
2. Click the "Authorize" button in Swagger UI
3. Enter your credentials
4. All subsequent requests will include authentication headers

## Example Usage

### Using cURL

```bash
# Ingest a PDF document
curl -X POST "http://localhost:8000/api/v1/documents/ingest" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.pdf"

# Query the knowledge base
curl -X POST "http://localhost:8000/api/v1/chat/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the main topic?", "max_results": 5}'
```

### Using Python

```python
import requests

# Ingest a PDF
with open('sample.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/documents/ingest',
        files={'file': f}
    )
    print(response.json())

# Query the knowledge base
response = requests.post(
    'http://localhost:8000/api/v1/chat/query',
    json={'query': 'What is the main topic?', 'max_results': 5}
)
print(response.json())
```

## Customization

The OpenAPI documentation can be customized in the FastAPI application:

- **Title and Description**: Set in the FastAPI app initialization
- **Version**: Configured via app metadata
- **Tags**: Organize endpoints into logical groups
- **Schemas**: Automatically generated from Pydantic models

## Troubleshooting

If the documentation is not accessible:

1. Ensure the FastAPI application is running
2. Check that the server is listening on the correct port (default: 8000)
3. Verify firewall/network settings allow access
4. Check application logs for errors
