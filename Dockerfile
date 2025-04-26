# ────────────────────────────────────────────────────────────────────────────┐
FROM python:3.10 AS base
# ────────────────────────────────────────────────────────────────────────────┘

WORKDIR /app

# Install Poetry (a dependency manager) and Uvicorn (a web application server).
RUN python -m pip install \
    poetry \
    uvicorn[standard]

# Use Poetry to install Python package dependencies; without installing the project, itself.
# Reference: https://python-poetry.org/docs/cli/#install
ADD poetry.lock    /app/poetry.lock
ADD pyproject.toml /app/pyproject.toml
RUN poetry install --no-interaction --no-root

EXPOSE 8000

# ────────────────────────────────────────────────────────────────────────────┐
FROM base AS production
# ────────────────────────────────────────────────────────────────────────────┘

# Copy the repository contents into the image.
COPY . /app

# Use Uvicorn to serve the FastAPI application on port 8000, accepting HTTP requests from any host.
# Reference: https://fastapi.tiangolo.com/deployment/manually/#run-the-server-program
CMD [ "uvicorn", "nmdc_orcid_creditor.main:app", "--host", "0.0.0.0", "--port", "8000" ]

# ────────────────────────────────────────────────────────────────────────────┐
FROM base AS development
# ────────────────────────────────────────────────────────────────────────────┘

# Install Node.js and NPM so we can use `$ npx prettier` to format JavaScript code.
RUN apt update && \
    apt install -y nodejs npm

# Run the FastAPI development server on port 8000, accepting HTTP requests from any host.
# Reference: https://fastapi.tiangolo.com/deployment/manually/
CMD [ "poetry", "run", "fastapi", "dev", "--host", "0.0.0.0", "/app/nmdc_orcid_creditor/main.py" ]
