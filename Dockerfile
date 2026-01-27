# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory to root first to copy requirements
WORKDIR /app

# Install dependencies
COPY requirements.txt .
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
