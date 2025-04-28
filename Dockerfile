"""
########################################################################
# AI Prompt Service - Dockerfile
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Add Postgres 16, add docker. Endpoint should work ad hoc (AS IS) or with session Mode.
# Version: 1.0.0
# Created: 2025-04-27
# 
# Purpose: Docker configuration for the AI Prompt Service
#
# Dependencies: Python 3.12
########################################################################

FROM python:3.12-slim

WORKDIR /app

# Install dependencies including PostgreSQL client
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set up environment
ENV PYTHONPATH=/app
ENV PORT=8000

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Expose the application port
EXPOSE 8000

# Run the application
CMD ["/app/entrypoint.sh"]