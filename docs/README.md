# Documentation

Welcome to the FastAPI Document Chat API documentation.

## Quick Links

- **[Quickstart Guide](quickstart.md)** - Get started in minutes with a complete end-to-end walkthrough
- **[OpenAPI Documentation](openapi.md)** - Learn about the interactive API documentation
- **[Environment Variables & Security](environment.md)** - Configuration reference and security best practices

## Getting Started

1. **New to the project?** Start with the [Quickstart Guide](quickstart.md)
2. **Want to explore the API?** Check out the [OpenAPI Documentation](openapi.md)
3. **Deploying to production?** Review the [Environment Variables & Security](environment.md) guide

## Documentation Structure

### Quickstart Guide

The quickstart guide provides a step-by-step walkthrough:
- Starting the application with Docker Compose
- Ingesting a sample PDF document
- Querying the chat interface
- Viewing citations
- Troubleshooting common issues

### OpenAPI Documentation

Learn how to use the automatically generated API documentation:
- Accessing Swagger UI and ReDoc
- Testing endpoints interactively
- Understanding request/response schemas
- Authentication and authorization

### Environment Variables & Security

Comprehensive reference for:
- All available environment variables
- Configuration for different environments
- Security model and best practices
- Production deployment checklist

## Using the Makefile

The project includes a Makefile for common tasks:

```bash
make run      # Start the application
make test     # Run tests
make lint     # Run linting checks
make load     # Ingest a sample PDF
make docs     # View documentation
make stop     # Stop the application
make clean    # Clean up containers and temporary files
```

For more details, run `make help` or see the [Quickstart Guide](quickstart.md).

## Additional Resources

- API Documentation (when running): http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- OpenAPI Schema: http://localhost:8000/openapi.json
