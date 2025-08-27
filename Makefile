.PHONY: install start start-docker test build ecr-create ecr-login ecr-push create-db-user test-db-connection init-db init-auth init-all

# Default environment variables
export ENV=development
ENV_FILE=docker/server/.env
export SERVER_VOLUME=.:/app

# Install dependencies
install:
	poetry install

# Initialize database with seed data
init-db:
	@echo "🗄️  Initializing database with seed data..."
	docker compose exec bazar-api poetry run python -m src.app.db.init_db
	@echo "✅ Database initialization completed!"

# Initialize Supabase authentication
init-auth:
	@echo "🔐 Initializing Supabase authentication..."
	docker compose exec bazar-api poetry run python -m src.app.db.init_auth
	@echo "✅ Authentication initialization completed!"

# Initialize both database and auth
init-all: init-db init-auth
	@echo "🚀 Complete initialization finished!"

# Verify database connection and show connection details
create-db-user:
	@echo "Verifying database connection..."
	@docker compose exec -T postgres psql -U bazar -d bazardev -c "SELECT current_user, current_database();" || echo "Database connection failed"
	@echo ""
	@echo "Database connection details for pgAdmin:"
	@echo "  Host: localhost (or 127.0.0.1)"
	@echo "  Port: 5432"
	@echo "  Database: bazardev"
	@echo "  Username: bazar"
	@echo "  Password: secret"
	@echo ""
	@echo "Database setup completed!"

# Test database connection from host machine (for pgAdmin)
test-db-connection:
	@echo "Testing database connection from host machine..."
	@docker run --rm --network bazar-api_default -e PGPASSWORD=secret postgres:14 psql -h postgres -U bazar -d bazardev -c "SELECT current_user, current_database();" || echo "Connection failed - make sure PostgreSQL container is running"

# Setup complete local development environment
setup-dev: create-db-user alembic-up init-all
	@echo "Local development environment is ready!"

# Build Docker image
build:
	docker buildx build --platform linux/amd64 -f docker/server/Dockerfile -t bazar-api .

# Create ECR repository
ecr-create:
	aws ecr create-repository --repository-name bazar-api --profile bazar-api

# Get ECR login token and login
ecr-login:
	aws ecr get-login-password --region us-east-1 --profile bazar-api | docker login --username AWS --password-stdin $(shell aws sts get-caller-identity --profile bazar-api --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Tag and push image to ECR
ecr-push: build
	$(eval ECR_REGISTRY := $(shell aws sts get-caller-identity --profile bazar-api --query Account --output text).dkr.ecr.us-east-1.amazonaws.com)
	docker tag bazar-api:latest $(ECR_REGISTRY)/bazar-api:latest
	docker push $(ECR_REGISTRY)/bazar-api:latest

# Start server using poetry (local development)
start:
	docker compose up

# Run alembic inside Docker container
alembic-up:
	docker compose exec bazar-api poetry run alembic upgrade head

# Downgrade to base (removes all tables)
alembic-down:
	docker compose exec bazar-api poetry run alembic downgrade base
