#!/bin/bash
set -e

echo "Starting Clinic Management Application..."

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
