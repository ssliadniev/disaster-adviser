#!/bin/bash
set -e

echo "Waiting for database to be ready..."
sleep 3

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"