#!/bin/bash
# Wait for database to be ready
echo "Waiting for database..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h db -U postgres -d prompt_service -c '\q' 2>/dev/null; do
  echo "Database is unavailable - sleeping 2s"
  sleep 2
done
echo "Database is ready!"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting application..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000