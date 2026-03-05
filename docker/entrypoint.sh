#!/bin/sh

set -e

echo "Waiting for postgres..."

# Wait for postgres logic (can be improved with wait-for-it.sh)
# For now, we rely on docker-compose depends_on healthcheck or just sleep

exec "$@"
