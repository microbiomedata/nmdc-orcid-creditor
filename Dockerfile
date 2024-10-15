FROM python:3.10

WORKDIR /app

# Install Node.js and NPM so we can use `$ npx prettier` to format JavaScript code.
RUN apt update && \
    apt install -y nodejs npm

# Install Poetry.
RUN python -m pip install poetry

# Use Poetry to install Python package dependencies.
# Reference: https://python-poetry.org/docs/cli/#install
ADD poetry.lock    /app/poetry.lock
ADD pyproject.toml /app/pyproject.toml
RUN poetry install

# Run the FastAPI development server, accepting HTTP requests from any host,
# include those outside of the container (e.g. the container host system).
# Reference: https://fastapi.tiangolo.com/deployment/manually/
EXPOSE 8000
CMD [ "poetry", "run", "fastapi", "dev", "--host", "0.0.0.0", "/app/nmdc_orcid_creditor/main.py" ]
