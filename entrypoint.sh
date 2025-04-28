#!/bin/bash
########################################################################
# AI Prompt Service - entrypoint.sh
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Add Postgres 16, add docker. Endpoint should work ad hoc (AS IS) or with session Mode.
# Version: 1.0.0
# Created: 2025-04-27
# 
# Purpose: Docker container entrypoint script to handle database initialization and app startup
#
# Dependencies: PostgreSQL client tools, Alembic, Uvicorn
########################################################################

set -e

# Wait for database to be ready
echo "Waiting for database to be ready..."
until PGPASSWORD=${POSTGRES_PASSWORD} psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c '\q' 2>/dev/null; do
  echo "Database is unavailable - sleeping 2s"
  sleep 5
done
echo "Database is ready!"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting application..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000