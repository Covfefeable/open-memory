#!/bin/sh

set -e

echo "Waiting for postgres..."

# Run database migrations if FLASK_APP is set (indicates we are running the API or Worker with Flask context)
if [ "$FLASK_APP" = "app" ] && [ "$FLASK_ENV" != "development" ]; then
    echo "Running database migrations..."
    uv run flask db upgrade
fi

exec "$@"
