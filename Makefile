.PHONY: dev prod test lint typecheck migrate db-init geoip clean deploy help

help:
	@echo "Tunnel - Available commands:"
	@echo "  make dev         - Start development environment with hot reload"
	@echo "  make prod        - Start production environment"
	@echo "  make test        - Run all tests"
	@echo "  make lint        - Run linters (ruff, eslint)"
	@echo "  make typecheck   - Run type checkers (mypy, tsc)"
	@echo "  make migrate     - Run database migrations"
	@echo "  make db-init     - Initialize database (run migrations + seed)"
	@echo "  make geoip       - Download GeoIP database"
	@echo "  make clean       - Clean up containers, volumes, and build artifacts"
	@echo "  make deploy      - Deploy to production VPS"

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

prod:
	docker compose up -d

test:
	docker compose exec api pytest tests/
	docker compose exec dashboard npm run test

lint:
	ruff check server/app/ cli/localdrop/
	cd client && npm run lint

typecheck:
	cd server && python -m mypy app/
	cd client && npx tsc --noEmit

migrate:
	docker compose exec api alembic upgrade head

db-init: migrate
	docker compose exec api python -m app.scripts.init_port_pool

geoip:
	docker compose exec api python -m app.scripts.download_geoip

clean:
	docker compose down -v --remove-orphans
	rm -rf server/app/__pycache__ cli/localdrop/__pycache__
	cd client && rm -rf node_modules/.vite

deploy:
	@echo "Deploying to production..."
	scp -r . user@your-vps:/opt/tunnel
	ssh user@your-vps "cd /opt/tunnel && make prod"
