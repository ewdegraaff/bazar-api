.PHONY: install start start-docker test build ecr-create ecr-login ecr-push

# Default environment variables
export ENV=development
ENV_FILE=docker/server/.env
export SERVER_VOLUME=.:/app

# Install dependencies
install:
	poetry install

# Build Docker image
build:
	docker build -f docker/server/Dockerfile -t bazar-api .

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
