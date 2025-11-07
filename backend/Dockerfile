# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY generative_agents /app

# Expose port
EXPOSE 5001

# Set environment variables
ENV FLASK_APP=app.py \
    PORT=5001

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5001", "--workers", "4", "--threads", "8"]
