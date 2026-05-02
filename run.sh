#!/bin/bash
set -e

# Wait for database to be ready with timeout
echo "Waiting for database to be ready..."
for i in {1..30}; do
    if python manage.py dbshell -c "SELECT 1" >/dev/null 2>&1; then
        echo "Database is ready!"
        break
    fi
    echo "Database not ready, waiting... ($i/30)"
    sleep 2
done

# Run migrations with error handling
echo "Running database migrations..."
python manage.py migrate --noinput || echo "⚠️  Warning: Migrations failed, continuing startup..."

# Start the server
echo "Starting Gunicorn server..."
exec gunicorn clinic_management.wsgi:application
