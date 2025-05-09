# ────────────────────────────────────────────────────────────────────────────┐
FROM python:3.12 AS base
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
#
# Note: We do the following 3 things to make ORCID Login work with this application when we host it
#       on NERSC's Spin (Kubernetes) platform and access it via Cloudflare:
#
#       1. We add the following annotation to the Kubernetes ingress, so that its underlying Nginx server
#          _forwards_ the `X-Forwarded-*` HTTP headers that it receives from Cloudflare, to Uvicorn:
#          ```
#          nginx.ingress.kubernetes.io/use-forwarded-headers: "true"
#          ```
#          Reference: https://www.uvicorn.org/deployment/#proxies-and-forwarded-headers
#
#       2. We use the environment variable `FORWARDED_ALLOW_IPS` (which is equivalent to the
#          `--forwarded-allow-ips` CLI option) to configure Uvicorn to _trust_ the `X-Forwarded-*`
#          headers it receives from the Kubernetes ingress. At the time of this writing, the
#          environment variable's value is:
#          ```
#          10.42.0.0/16,128.55.137.128/25,128.55.206.0/24
#          ```
#          Those IP addresses are publicly advertised in the "Configuration for nginx" section of the following NERSC Spin FAQ entry:
#          https://docs.nersc.gov/services/spin/faq/#why-are-ip-addresses-in-the-10420016-range-showing-in-my-web-service-access-log
#
#       3. We include the `--proxy-headers` CLI option (here) so that Uvicorn _uses_ the `X-Forwarded-*`
#          HTTP headers that it receives from the Kubernetes ingress.
#          Reference: https://github.com/encode/starlette/issues/538#issuecomment-518748568
#
# Reference: https://fastapi.tiangolo.com/deployment/manually/#run-the-server-program
#
CMD [ "poetry", "run", "uvicorn", "nmdc_orcid_creditor.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers" ]

# ────────────────────────────────────────────────────────────────────────────┐
FROM base AS development
# ────────────────────────────────────────────────────────────────────────────┘

# Install Node.js and NPM so we can use `$ npx prettier` to format JavaScript code.
RUN apt update && \
    apt install -y nodejs npm

# Run the FastAPI development server on port 8000, accepting HTTP requests from any host.
# Reference: https://fastapi.tiangolo.com/deployment/manually/
CMD [ "poetry", "run", "fastapi", "dev", "--host", "0.0.0.0", "/app/nmdc_orcid_creditor/main.py" ]
