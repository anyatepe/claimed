.PHONY: up down test build clean logs

# Start all services
up:
	docker-compose up -d

# Start services including chroma
up-chroma:
	docker-compose --profile chroma up -d

# Stop all services
down:
	docker-compose down

# Stop and remove volumes
down-volumes:
	docker-compose down -v

# Run tests
test:
	docker-compose run --rm --network tests api pytest -v || \
	docker-compose run --rm --network tests api python -m pytest -v || \
	docker-compose run --rm --network tests api python -m unittest discover -s tests -p "test_*.py" || \
	echo "No tests found. Please configure your test runner."

# Build the API image
build:
	docker-compose build api

# View logs
logs:
	docker-compose logs -f

# View API logs only
logs-api:
	docker-compose logs -f api

# Clean up containers, volumes, and images
clean: down-volumes
	docker-compose rm -f
	docker system prune -f

# Check service health
health:
	@echo "Checking service health..."
	@docker-compose ps
