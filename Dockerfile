# Use official Python runtime as a parent image
# Build trigger: 2026-02-01 (V5.2.4.4 SSL & Stability Shield)
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# V5.2.4.4: Force native DNS resolver for Google API stability in Cloud Run
ENV GRPC_DNS_RESOLVER native

# Set work directory
WORKDIR /app

# Install system dependencies for crypto and robust SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    ca-certificates \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Update CA Certificates to ensure SSL handshake stability
RUN update-ca-certificates

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip uninstall -y pycrypto pycryptodome && pip install --no-cache-dir pycryptodome==3.20.0
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Change to backend directory for execution
WORKDIR /app/1CRYPTEN_SPACE_V4.0/backend

# Expose port (Cloud Run defaults to 8080)
ENV PORT 8080
EXPOSE 8080

# Command to run the application using Gunicorn (Production Standard)
CMD exec gunicorn --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 8 --timeout 0 main:app
