.PHONY: dev stop logs test clean

# Build and run locally with docker compose
dev:
	docker compose -f docker-compose.dev.yml up --build -d
	@echo "✓ Running at http://localhost:8001"

# Stop local container
stop:
	docker compose -f docker-compose.dev.yml down

# Follow container logs
logs:
	docker compose -f docker-compose.dev.yml logs -f

# Quick smoke test: health + tool list
test:
	@echo "--- Health ---"
	@curl -sf http://localhost:8001/health | python3 -m json.tool
	@echo "\n--- MCP Tools (via discover) ---"
	@MCP_API_KEY=$$(grep MCP_API_KEY .env | cut -d= -f2); \
	curl -sf -H "Authorization: Bearer $$MCP_API_KEY" http://localhost:8001/health | python3 -m json.tool
	@echo "✓ Server is healthy"

# Run python module directly (no container)
run:
	python -m src

# Remove local dev container and image
clean:
	docker compose -f docker-compose.dev.yml down --rmi local --volumes
