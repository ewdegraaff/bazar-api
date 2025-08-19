from setuptools import setup, find_packages

setup(
    name="bazar-api",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "alembic",
        "psycopg2-binary",
        "pydantic",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "python-multipart",
        "pyyaml",
    ],
) 