# RAG PDF Chat

A FastAPI-based Retrieval-Augmented Generation (RAG) service for chatting with PDF documents.

## Features

- **PDF Document Ingestion**: Upload and process PDF documents
- **Vector Search**: Semantic search using embeddings and vector stores
- **RAG Chat**: Chat with documents using retrieval-augmented generation
- **Multiple Vector Stores**: Support for Pinecone and ChromaDB
- **Chat Memory**: Conversation history management
- **Production Ready**: Docker, docker-compose, and Helm charts included

## Project Structure

```
rag_pdf_chat/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── api/                    # API routers
│   │   ├── chat.py            # Chat endpoints
│   │   ├── ingestion.py       # Document ingestion endpoints
│   │   └── health.py          # Health check endpoints
│   ├── services/              # Business logic services
│   │   ├── rag.py             # RAG service
│   │   ├── embeddings.py      # Embeddings service
│   │   ├── vector_store.py    # Vector store service
│   │   ├── ingestion.py       # Ingestion service
│   │   ├── llm.py             # LLM service
│   │   └── chat_memory.py     # Chat memory service
│   ├── adapters/              # External service adapters
│   │   ├── pinecone_store.py # Pinecone adapter
│   │   ├── chroma_store.py    # ChromaDB adapter
│   │   └── langflow_client.py # Langflow client
│   ├── models/                # Pydantic models
│   │   ├── chat.py           # Chat models
│   │   └── ingestion.py      # Ingestion models
│   ├── utils/                 # Utility modules
│   │   ├── cache.py          # Redis cache
│   │   ├── auth.py           # Authentication
│   │   ├── idempotency.py    # Idempotency handling
│   │   ├── logging.py        # Structured logging
│   │   └── tracing.py        # OpenTelemetry tracing
│   └── tests/                # Test suite
├── infra/
│   ├── docker-compose.yml    # Local development setup
│   ├── Dockerfile            # Application Dockerfile
│   └── helm/                 # Kubernetes Helm charts
├── pyproject.toml            # Project configuration (ruff, mypy)
├── requirements.txt          # Python dependencies
├── Dockerfile                # Root Dockerfile
└── README.md                 # This file
```

## Requirements

- Python 3.11+
- Docker and Docker Compose (for local development)
- Redis (for caching and chat memory)
- PostgreSQL (optional, for persistent storage)
- Vector store: Pinecone or ChromaDB

## Installation

1. Clone the repository:
```bash
cd LearningPlatform/LearningAssistant/rag_pdf_chat
```

2. Create a virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set environment variables:
```bash
export REDIS_URL="redis://localhost:6379"
export PINECONE_API_KEY="your-pinecone-api-key"  # Optional
export PINECONE_INDEX_NAME="rag-chat"  # Optional
export LANGFLOW_URL="http://localhost:7860"  # Optional
export SECRET_KEY="your-secret-key"  # For JWT tokens
```

## Running Locally

### Using Docker Compose

```bash
cd infra
docker-compose up
```

This will start:
- FastAPI application on port 8000
- Redis on port 6379
- PostgreSQL on port 5432

### Using Python directly

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Checks
- `GET /health/` - Basic health check
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness check

### Chat
- `POST /api/v1/chat/` - Send a chat message

### Ingestion
- `POST /api/v1/ingestion/pdf` - Upload and ingest a PDF document
- `DELETE /api/v1/ingestion/{document_id}` - Delete a document

## Development

### Code Quality

The project uses:
- **ruff** for linting and formatting
- **mypy** for type checking

Run linting:
```bash
ruff check app/
ruff format app/
```

Run type checking:
```bash
mypy app/
```

### Testing

Run tests:
```bash
pytest app/tests/
```

## Production Deployment

### Docker

Build the image:
```bash
docker build -t rag-pdf-chat:latest .
```

Run the container:
```bash
docker run -p 8000:8000 rag-pdf-chat:latest
```

### Kubernetes

Helm charts are available in `infra/helm/` for Kubernetes deployment.

## Configuration

Key environment variables:
- `REDIS_URL`: Redis connection URL
- `PINECONE_API_KEY`: Pinecone API key (if using Pinecone)
- `PINECONE_INDEX_NAME`: Pinecone index name
- `LANGFLOW_URL`: Langflow API URL
- `SECRET_KEY`: Secret key for JWT tokens
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `OTLP_ENDPOINT`: OpenTelemetry endpoint for tracing

## License

[Add your license here]
