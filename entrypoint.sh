#!/bin/bash
set -e

echo "Waiting for database..."
# Wait for database to be ready (already handled by depends_on + healthcheck)

# Only apply existing migrations - don't create new ones
# Migrations should be created during development and committed to git
# For initial setup, ensure migrations/ directory is included in the repository
if [ -d "migrations" ]; then
    echo "Running database migrations..."
    flask db upgrade
else
    echo "WARNING: No migrations directory found!"
    echo "Migrations should be committed to version control."
    echo "If this is initial setup, create migrations with:"
    echo "  flask db init"
    echo "  flask db migrate -m 'Initial migration'"
    echo "  flask db upgrade"
    echo "Skipping migrations for now..."
fi

echo "Starting application..."
exec "$@"