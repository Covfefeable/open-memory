#!/bin/sh

set -e

echo "Waiting for postgres..."

# Run database migrations if RUN_MIGRATIONS is set to true
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    uv run --no-sync flask db upgrade
fi

exec "$@"
