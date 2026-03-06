#!/bin/bash
set -e

echo "Starting Face Attendance API..."

# Wait for database to be ready
echo "Waiting for database..."
sleep 5

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Seed initial data if database is empty (optional)
# Uncomment if you want to auto-seed on first deployment
# echo "Seeding database (if empty)..."
# python scripts/db_manager.py seed 2>/dev/null || echo "Database already seeded or seed failed"

echo "Starting application..."
# Execute the command passed to the script (from CMD in Dockerfile)
exec "$@"
