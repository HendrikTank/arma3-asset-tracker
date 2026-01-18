#!/bin/bash
set -e

echo "Waiting for database..."
# Wait for database to be ready (already handled by depends_on + healthcheck)

# Check if migrations directory exists
if [ ! -d "migrations" ]; then
    echo "Initializing Flask-Migrate..."
    flask db init
    echo "Creating initial migration..."
    flask db migrate -m "Initial migration"
fi

echo "Running database migrations..."
flask db upgrade

echo "Starting application..."
exec "$@"