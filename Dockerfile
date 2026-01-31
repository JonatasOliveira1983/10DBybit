# Use official Python runtime as a parent image
# Build trigger: 2026-01-30 23:11 (V5.0.4 SSL Fix)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory to root first to copy requirements
WORKDIR /app

# Install system dependencies for crypto and build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies (Hardening Crypto)
COPY requirements.txt .
RUN pip install --upgrade pip
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
