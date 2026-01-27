# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose port (Cloud Run defaults to 8080)
ENV PORT 8080
EXPOSE 8080

# Command to run the application
# We use shell form to properly expand the PORT variable and change directory
CMD ["sh", "-c", "cd 1CRYPTEN_SPACE_V4.0/backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
