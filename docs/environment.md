# Environment Variables Reference

This document describes all environment variables used by the FastAPI application and provides guidance on the security model.

## Application Configuration

### Core Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_HOST` | Host address to bind the API server | `0.0.0.0` | No |
| `API_PORT` | Port number for the API server | `8000` | No |
| `API_RELOAD` | Enable auto-reload for development | `false` | No |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` | No |
| `ENVIRONMENT` | Environment name (development, staging, production) | `development` | No |

### API Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_TITLE` | API title shown in OpenAPI docs | `Document Chat API` | No |
| `API_VERSION` | API version | `1.0.0` | No |
| `API_DESCRIPTION` | API description | `RAG-based document chat API` | No |
| `CORS_ORIGINS` | Comma-separated list of allowed CORS origins | `*` | No |
| `MAX_UPLOAD_SIZE` | Maximum file upload size in bytes | `10485760` (10MB) | No |
| `ALLOWED_EXTENSIONS` | Comma-separated list of allowed file extensions | `pdf` | No |

## Vector Database Configuration

### Qdrant

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `QDRANT_HOST` | Qdrant server host | `localhost` | Yes |
| `QDRANT_PORT` | Qdrant server port | `6333` | No |
| `QDRANT_API_KEY` | Qdrant API key for authentication | - | No |
| `QDRANT_COLLECTION_NAME` | Name of the Qdrant collection | `documents` | No |
| `QDRANT_TIMEOUT` | Connection timeout in seconds | `30` | No |

### Chroma (Alternative)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CHROMA_HOST` | Chroma server host | `localhost` | Yes (if using Chroma) |
| `CHROMA_PORT` | Chroma server port | `8000` | No |
| `CHROMA_COLLECTION_NAME` | Name of the Chroma collection | `documents` | No |

### Pinecone (Alternative)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PINECONE_API_KEY` | Pinecone API key | - | Yes (if using Pinecone) |
| `PINECONE_ENVIRONMENT` | Pinecone environment | - | Yes (if using Pinecone) |
| `PINECONE_INDEX_NAME` | Pinecone index name | `documents` | No |

## LLM Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LLM_PROVIDER` | LLM provider (openai, anthropic, local) | `openai` | Yes |
| `OPENAI_API_KEY` | OpenAI API key | - | Yes (if using OpenAI) |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4-turbo-preview` | No |
| `OPENAI_TEMPERATURE` | Model temperature (0-2) | `0.7` | No |
| `OPENAI_MAX_TOKENS` | Maximum tokens in response | `1000` | No |
| `ANTHROPIC_API_KEY` | Anthropic API key | - | Yes (if using Anthropic) |
| `ANTHROPIC_MODEL` | Anthropic model name | `claude-3-opus-20240229` | No |
| `LOCAL_MODEL_PATH` | Path to local model | - | Yes (if using local) |
| `EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-small` | No |
| `EMBEDDING_DIMENSION` | Embedding vector dimension | `1536` | No |

## Document Processing

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CHUNK_SIZE` | Text chunk size for splitting | `1000` | No |
| `CHUNK_OVERLAP` | Overlap between chunks | `200` | No |
| `PDF_EXTRACT_IMAGES` | Extract images from PDFs | `false` | No |
| `PDF_EXTRACT_TABLES` | Extract tables from PDFs | `true` | No |
| `MAX_CHUNKS_PER_DOCUMENT` | Maximum chunks per document | `1000` | No |

## Database Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Database connection string | - | No |
| `DATABASE_POOL_SIZE` | Database connection pool size | `10` | No |
| `DATABASE_MAX_OVERFLOW` | Maximum overflow connections | `20` | No |

## Cache Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REDIS_HOST` | Redis server host | `localhost` | No |
| `REDIS_PORT` | Redis server port | `6379` | No |
| `REDIS_PASSWORD` | Redis password | - | No |
| `REDIS_DB` | Redis database number | `0` | No |
| `CACHE_TTL` | Cache time-to-live in seconds | `3600` | No |

## Authentication & Security

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_KEY` | API key for authentication | - | No |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | - | No |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` | No |
| `JWT_EXPIRATION_HOURS` | JWT token expiration time | `24` | No |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` | No |
| `RATE_LIMIT_REQUESTS` | Requests per minute | `60` | No |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds | `60` | No |

## Monitoring & Observability

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENABLE_METRICS` | Enable Prometheus metrics | `true` | No |
| `METRICS_PORT` | Port for metrics endpoint | `9090` | No |
| `ENABLE_TRACING` | Enable OpenTelemetry tracing | `false` | No |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry endpoint | - | No |
| `SENTRY_DSN` | Sentry DSN for error tracking | - | No |

## Storage Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `STORAGE_TYPE` | Storage type (local, s3, gcs) | `local` | No |
| `STORAGE_PATH` | Local storage path | `./storage` | No |
| `S3_BUCKET` | S3 bucket name | - | Yes (if using S3) |
| `S3_REGION` | AWS region | `us-east-1` | No |
| `AWS_ACCESS_KEY_ID` | AWS access key | - | Yes (if using S3) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | - | Yes (if using S3) |

## Example Configuration Files

### Development (.env.development)

```bash
ENVIRONMENT=development
API_RELOAD=true
LOG_LEVEL=DEBUG
QDRANT_HOST=localhost
QDRANT_PORT=6333
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Production (.env.production)

```bash
ENVIRONMENT=production
API_RELOAD=false
LOG_LEVEL=INFO
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_API_KEY=your-secure-api-key
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
API_KEY=your-api-key-here
JWT_SECRET_KEY=your-jwt-secret-key
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=60
ENABLE_METRICS=true
SENTRY_DSN=https://...
```

## Security Model

### Authentication

The application supports multiple authentication methods:

1. **API Key Authentication**: Simple API key passed via header
   ```bash
   curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/...
   ```

2. **JWT Authentication**: Token-based authentication for user sessions
   ```bash
   curl -H "Authorization: Bearer your-jwt-token" http://localhost:8000/api/v1/...
   ```

3. **No Authentication**: For development/testing (not recommended for production)

### Authorization

- **Public Endpoints**: Health check, API documentation
- **Authenticated Endpoints**: All `/api/v1/*` endpoints require authentication
- **Admin Endpoints**: Document deletion, system configuration (require admin role)

### Rate Limiting

Rate limiting is enforced to prevent abuse:

- Default: 60 requests per minute per IP
- Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`
- Returns `429 Too Many Requests` when exceeded

### Input Validation

- File uploads: Validated by extension and size
- Query parameters: Validated using Pydantic models
- SQL injection prevention: Parameterized queries
- XSS prevention: Input sanitization

### Secrets Management

**Never commit secrets to version control!**

1. **Development**: Use `.env` files (add to `.gitignore`)
2. **Production**: Use secret management services:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Kubernetes Secrets
   - Docker Secrets

### Network Security

- **CORS**: Configure allowed origins via `CORS_ORIGINS`
- **HTTPS**: Always use HTTPS in production (configure reverse proxy)
- **Firewall**: Restrict access to necessary ports only
- **Internal Networks**: Use private networks for service communication

### Data Security

- **Encryption at Rest**: Enable for sensitive document storage
- **Encryption in Transit**: Use TLS/SSL for all connections
- **Data Isolation**: Separate databases/collections per tenant (if multi-tenant)
- **Data Retention**: Implement policies for document deletion

### Best Practices

1. **Rotate Secrets Regularly**: Change API keys, JWT secrets periodically
2. **Use Strong Secrets**: Generate random, long secrets (minimum 32 characters)
3. **Principle of Least Privilege**: Grant minimum necessary permissions
4. **Monitor Access**: Log all authentication attempts and API calls
5. **Update Dependencies**: Keep all dependencies up to date
6. **Security Headers**: Configure security headers (CSP, HSTS, etc.)
7. **Regular Audits**: Review logs and access patterns regularly

### Security Checklist for Production

- [ ] All secrets stored in secure vault (not in code/config files)
- [ ] HTTPS enabled with valid SSL certificate
- [ ] API authentication enabled (`API_KEY` or `JWT_SECRET_KEY` set)
- [ ] Rate limiting enabled
- [ ] CORS configured with specific origins (not `*`)
- [ ] File upload size limits configured
- [ ] Input validation enabled for all endpoints
- [ ] Logging configured (without sensitive data)
- [ ] Monitoring and alerting set up
- [ ] Regular security updates scheduled
- [ ] Backup and disaster recovery plan in place

## Environment-Specific Recommendations

### Development

- Use `.env` files for local configuration
- Enable debug logging
- Disable rate limiting
- Use local services (no external APIs)

### Staging

- Mirror production configuration
- Use test API keys
- Enable monitoring
- Test authentication flows

### Production

- Use secret management services
- Enable all security features
- Configure monitoring and alerting
- Set up backup and recovery
- Use production-grade infrastructure
