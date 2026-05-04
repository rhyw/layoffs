#!/bin/bash
set -e

# Wait for PostgreSQL to be ready (only if DATABASE_URL points to PostgreSQL)
if [[ "$DATABASE_URL" == postgres://* ]] || [[ "$DATABASE_URL" == postgresql://* ]]; then
    echo "Waiting for database..."
    until python -c "
import psycopg2
from urllib.parse import urlparse
import os
url = urlparse(os.environ['DATABASE_URL'])
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

# Only run migrations/seeds from the web container (others just need the DB up)
if [[ "$1" == gunicorn* ]]; then
    echo "Running migrations..."
    python manage.py migrate --noinput

    echo "Seeding data sources..."
    python manage.py seed_datasources --noinput 2>/dev/null || true

    # Load sample data if DB is empty (idempotent — skips if events exist)
    python manage.py shell -c "
from layoffs.models import LayoffEvent
if LayoffEvent.objects.count() == 0:
    __import__('subprocess').check_call(['python', 'manage.py', 'loaddata', 'layoffs_2026_04'])
    print('Loaded sample data fixture.')
else:
    print('Database already has data, skipping fixture load.')
" 2>/dev/null || true
fi

# Start the application
echo "Starting server..."
exec "$@"
