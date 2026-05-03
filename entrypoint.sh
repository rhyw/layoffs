#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    until python -c "
import psycopg2
from urllib.parse import urlparse
url = urlparse('$DATABASE_URL')
conn = psycopg2.connect(
    dbname=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port or 5432
)
conn.close()
" 2>/dev/null; do
    sleep 1
done
    echo "Database ready!"
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Seed data sources (idempotent)
echo "Seeding data sources..."
python manage.py seed_datasources --noinput 2>/dev/null || true

# Start the application
echo "Starting server..."
exec "$@"
