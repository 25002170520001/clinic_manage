#!/bin/bash
set -e

echo "Starting Clinic Management Application..."

echo "Waiting for database to become reachable..."
for i in {1..12}; do
    if python - <<'PY' >/dev/null 2>&1
import os
from urllib.parse import urlparse
from socket import gethostbyname

database_url = os.environ.get("DATABASE_URL", "")
host = urlparse(database_url).hostname
if not host:
    raise SystemExit(1)

gethostbyname(host)
PY
    then
        echo "✓ Database host resolved"
        break
    fi

    if [ $i -lt 12 ]; then
        echo "Database not ready yet, retrying in 5 seconds..."
        sleep 5
    fi
done

# Try running migrations with basic retry
for i in {1..3}; do
    echo "Attempt $i: Running migrations..."
    if python manage.py migrate --noinput 2>&1; then
        echo "✓ Migrations completed"
        break
    fi
    if [ $i -lt 3 ]; then
        echo "Migration failed, retrying in 5 seconds..."
        sleep 5
    fi
done

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear >/dev/null 2>&1

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn clinic_management.wsgi:application --bind 0.0.0.0:10000
