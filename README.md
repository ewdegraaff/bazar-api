# Bazar API

## Overview
This repository contains a FastAPI-based backend application designed to manage organizations, users, and role-based access control. It uses Supabase for authentication and PostgreSQL for data storage, with Alembic for database migrations.

## Project Structure
```
.
├── README.md
├── Makefile, run-tests.sh, start-dev.sh
├── docker/, docker-compose.yml, .dockerignore
├── pyproject.toml, .pre-commit-config.yaml, .gitignore
├── poetry_scripts.py
└── src/
    └── app/
        ├── main.py
        ├── core/
        │   ├── config.py
        │   └── events.py
        ├── api/
        │   ├── deps.py
        │   └── api_v1/
        │       ├── api.py
        │       └── endpoints/
        │           ├── auth.py
        │           ├── users.py
        │           └── organizations.py
        ├── crud/
        │   ├── base.py
        │   ├── crud_user.py
        │   └── crud_organization.py
        ├── schemas/
        │   ├── base.py
        │   ├── user.py
        │   ├── organization.py
        │   ├── auth.py
        │   └── ...
        ├── services/
        │   └── auth_service.py
        └── utils/
            └── auth.py, validation.py
```

## Key Features
- **FastAPI**: Modern, fast web framework for building APIs.
- **Supabase**: Authentication and database backend.
- **PostgreSQL**: Primary database, with Alembic for migrations.
- **Role-Based Access Control (RBAC)**: User plans (`Free`, `Plus`, `Premium`) with granular permissions for users and files managed via application-layer policies.
- **Global Error Handling**: Centralized error logging for future integration with cloud-based logging services.
- **Docker**: Containerized development and deployment.

## Setup Instructions
1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   ```

2. **Install Dependencies**:
   ```bash
   # Install poetry if not already installed
   curl -sSL https://install.python-poetry.org | python3 -

   # Install all project dependencies (including dev dependencies)
   poetry install
   ```

3. **Environment Variables**:
   - Create a `.env` file in the `docker/server/` directory for local development.
   - Required variables:
     ```
     SUPABASE_URL=your_supabase_url
     SUPABASE_KEY=your_supabase_key
     SUPERUSER_EMAIL=your_superuser_email
     SUPERUSER_PASSWORD=your_superuser_password
     DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bazardev
     ```

4. **Database Setup**:
   ```bash
   # Create database
   createdb bazardev

   # Run migrations
   poetry run alembic upgrade head
   ```

5. **Run the Application**:
   ```bash
   # Development mode with auto-reload
   poetry run python run.py

   # Or using uvicorn directly
   make start
   ```

## Development
- **Linting**: Uses Ruff and Pylance. Run `poetry run ruff check .` to lint the codebase.
- **Pre-commit Hooks**: Configured via `.pre-commit-config.yaml`.
- **Database Migrations**:
  ```bash
  # Create new migration
  poetry run alembic revision --autogenerate -m "Description"

  # Apply migrations
  poetry run alembic upgrade head

  # Rollback migration
  poetry run alembic downgrade -1
  ```

## API Endpoints
- **Authentication**: `/api/v1/auth/`
  - POST `/login`: Login with email/password
  - POST `/refresh`: Refresh access token

- **Users**: `/api/v1/users/`
  - GET `/`: List users
  - POST `/`: Create user
  - GET `/me`: Get current user
  - GET `/{id}`: Get user by ID
  - PUT `/{id}`: Update user
  - DELETE `/{id}`: Delete user



## Role-Based Access Control
- **Free**: Can read users and files
- **Plus**: Can read and execute files (workflow invocation)
- **Premium**: Full access to create, read, update, and delete users and files

## License
[Specify your license here]

## Database Setup and Migrations

### Prerequisites
- PostgreSQL 12 or higher
- Python 3.9 or higher
- Poetry for dependency management

### Database Configuration
1. Create a PostgreSQL database:
```bash
createdb bazardev
```

2. Set up the database URL (optional, defaults to localhost), see .env.example in docker folder

### Running Migrations

1. Install dependencies:
```bash
# Install poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install all project dependencies (including dev dependencies)
poetry install
```

2. Create a new migration:
```bash
poetry run alembic revision --autogenerate -m "create_all_tables"
```

3. Apply the migration:
```bash
poetry run alembic upgrade head
```

4. To rollback the last migration:
```bash
poetry run alembic downgrade -1
```

### Migration Commands

- Create a new migration:
```bash
poetry run alembic revision --autogenerate -m "description_of_changes"
```

- Apply all pending migrations:
```bash
poetry run alembic upgrade head
```

- Rollback one migration:
```bash
poetry run alembic downgrade -1
```

- Rollback all migrations:
```bash
poetry run alembic downgrade base
```

- Check current migration version:
```bash
poetry run alembic current
```

- List all migrations:
```bash
poetry run alembic history
```

### Development

1. Start the development server:
```bash
make start
```

### Docker Support

1. Build and start the containers:
```bash
docker-compose up --build
```

2. Run migrations in Docker:
```bash
docker-compose exec api poetry run alembic upgrade head
```

### Troubleshooting

1. If migrations fail, check:
   - Database connection settings
   - PostgreSQL service is running
   - Database exists and is accessible
   - User has proper permissions
   - All dependencies are installed correctly (run `poetry install` to ensure)

2. To reset the database:
```bash
make reset-db
```

3. To view migration history:
```bash
poetry run alembic history --verbose
```

4. To check current database state:
```bash
poetry run alembic current
```

### Best Practices

1. Always create new migrations for schema changes
2. Test migrations both up and down
3. Keep migrations atomic and focused
4. Review auto-generated migrations before applying
5. Back up the database before major migrations
6. Use meaningful migration names
7. Document any manual steps required



