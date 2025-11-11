.PHONY: help run stop test lint load docs clean install

# Default target
help:
	@echo "Available targets:"
	@echo "  make run      - Start the application using docker-compose"
	@echo "  make stop     - Stop the application"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Run linting checks"
	@echo "  make load     - Load sample data (ingest sample PDF)"
	@echo "  make docs     - Generate and serve documentation"
	@echo "  make clean    - Clean up containers, volumes, and temporary files"
	@echo "  make install  - Install dependencies"

# Variables
COMPOSE_FILE ?= docker-compose.yml
SAMPLE_PDF ?= sample.pdf
API_URL ?= http://localhost:8000

# Start the application
run:
	@echo "Starting application with docker-compose..."
	@if [ -f $(COMPOSE_FILE) ]; then \
		docker-compose -f $(COMPOSE_FILE) up -d; \
		echo "Waiting for services to be ready..."; \
		sleep 5; \
		echo "Application should be running at $(API_URL)"; \
		echo "API docs available at $(API_URL)/docs"; \
	else \
		echo "Error: $(COMPOSE_FILE) not found. Creating a basic docker-compose.yml..."; \
		@echo "Please create docker-compose.yml first"; \
		exit 1; \
	fi

# Stop the application
stop:
	@echo "Stopping application..."
	@if [ -f $(COMPOSE_FILE) ]; then \
		docker-compose -f $(COMPOSE_FILE) down; \
	else \
		echo "Warning: $(COMPOSE_FILE) not found"; \
	fi

# Run tests
test:
	@echo "Running tests..."
	@if command -v pytest >/dev/null 2>&1; then \
		pytest tests/ -v --cov=. --cov-report=html --cov-report=term; \
	elif [ -d tests ]; then \
		python -m pytest tests/ -v; \
	else \
		echo "No tests directory found. Creating basic test structure..."; \
		mkdir -p tests; \
		echo "# Add your tests here" > tests/__init__.py; \
		echo "Tests directory created. Please add your tests."; \
	fi

# Run linting
lint:
	@echo "Running linting checks..."
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check . --fix; \
	elif command -v flake8 >/dev/null 2>&1; then \
		flake8 . --max-line-length=100 --extend-ignore=E203,W503; \
	elif command -v pylint >/dev/null 2>&1; then \
		find . -name "*.py" -not -path "./.git/*" -not -path "./venv/*" -not -path "./env/*" | xargs pylint --disable=C0111; \
	else \
		echo "No linter found. Installing ruff..."; \
		pip install ruff || echo "Please install a linter (ruff, flake8, or pylint)"; \
	fi
	@if command -v black >/dev/null 2>&1; then \
		echo "Formatting code with black..."; \
		black . --check --diff || black .; \
	fi
	@if command -v mypy >/dev/null 2>&1 && [ -f pyproject.toml ] || [ -f setup.cfg ]; then \
		echo "Running type checking with mypy..."; \
		mypy . --ignore-missing-imports || true; \
	fi

# Load sample data
load:
	@echo "Loading sample PDF..."
	@if [ ! -f $(SAMPLE_PDF) ]; then \
		echo "Error: $(SAMPLE_PDF) not found."; \
		echo "Please provide a sample PDF file or set SAMPLE_PDF variable."; \
		echo "Example: make load SAMPLE_PDF=path/to/your/file.pdf"; \
		exit 1; \
	fi
	@echo "Checking if API is running..."
	@if ! curl -s $(API_URL)/health > /dev/null 2>&1; then \
		echo "Error: API is not running. Please run 'make run' first."; \
		exit 1; \
	fi
	@echo "Ingesting $(SAMPLE_PDF)..."
	@DOC_ID=$$(curl -s -X POST "$(API_URL)/api/v1/documents/ingest" \
		-H "Content-Type: multipart/form-data" \
		-F "file=@$(SAMPLE_PDF)" | grep -o '"document_id":"[^"]*"' | cut -d'"' -f4); \
	if [ -n "$$DOC_ID" ]; then \
		echo "Document ingested successfully! Document ID: $$DOC_ID"; \
		echo "Waiting for processing..."; \
		sleep 10; \
		echo "Checking document status..."; \
		curl -s "$(API_URL)/api/v1/documents/$$DOC_ID" | python -m json.tool 2>/dev/null || echo "Document status check completed"; \
	else \
		echo "Error: Failed to ingest document. Check API logs."; \
		exit 1; \
	fi

# Generate and serve documentation
docs:
	@echo "Generating documentation..."
	@if [ -d docs ]; then \
		echo "Documentation directory exists."; \
		if command -v mkdocs >/dev/null 2>&1 && [ -f mkdocs.yml ]; then \
			echo "Building MkDocs documentation..."; \
			mkdocs build; \
			echo "Serving documentation at http://localhost:8001"; \
			mkdocs serve --dev-addr=127.0.0.1:8001 & \
		elif command -v sphinx-build >/dev/null 2>&1 && [ -f docs/conf.py ]; then \
			echo "Building Sphinx documentation..."; \
			cd docs && make html; \
		else \
			echo "Documentation files found in docs/ directory:"; \
			ls -la docs/; \
			echo ""; \
			echo "To view OpenAPI docs, ensure the API is running and visit:"; \
			echo "  $(API_URL)/docs (Swagger UI)"; \
			echo "  $(API_URL)/redoc (ReDoc)"; \
			echo ""; \
			echo "To serve markdown docs, you can use:"; \
			echo "  python -m http.server 8001 -d docs"; \
		fi; \
	else \
		echo "Error: docs/ directory not found"; \
		exit 1; \
	fi

# Install dependencies
install:
	@echo "Installing dependencies..."
	@if [ -f requirements.txt ]; then \
		pip install -r requirements.txt; \
	elif [ -f pyproject.toml ]; then \
		pip install -e .; \
	else \
		echo "No requirements.txt or pyproject.toml found."; \
		echo "Installing common FastAPI dependencies..."; \
		pip install fastapi uvicorn[standard] pydantic python-multipart || true; \
	fi
	@if [ -f requirements-dev.txt ]; then \
		echo "Installing development dependencies..."; \
		pip install -r requirements-dev.txt; \
	fi

# Clean up
clean:
	@echo "Cleaning up..."
	@if [ -f $(COMPOSE_FILE) ]; then \
		docker-compose -f $(COMPOSE_FILE) down -v; \
	fi
	@echo "Removing Python cache files..."
	@find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true
	@echo "Removing coverage reports..."
	@rm -rf htmlcov/ .coverage coverage.xml 2>/dev/null || true
	@echo "Cleanup complete!"

# Additional useful targets

# Restart the application
restart: stop run

# View logs
logs:
	@if [ -f $(COMPOSE_FILE) ]; then \
		docker-compose -f $(COMPOSE_FILE) logs -f; \
	else \
		echo "Error: $(COMPOSE_FILE) not found"; \
	fi

# Check application health
health:
	@echo "Checking application health..."
	@curl -s $(API_URL)/health | python -m json.tool 2>/dev/null || echo "Health check endpoint not available"

# Query the chat API (example)
query:
	@echo "Example query to chat API:"
	@echo "curl -X POST '$(API_URL)/api/v1/chat/query' \\"
	@echo "  -H 'Content-Type: application/json' \\"
	@echo "  -d '{\"query\": \"What is this document about?\", \"max_results\": 5}'"
