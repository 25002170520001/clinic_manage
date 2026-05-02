#!/bin/bash
set -e

echo "Starting Clinic Management Application..."

# Try migrations multiple times with backoff
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Attempting migrations... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
    if python manage.py migrate --noinput; then
        echo "✓ Migrations completed successfully"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        WAIT_TIME=$((2 ** RETRY_COUNT))
        echo "⚠️  Migrations failed, retrying in ${WAIT_TIME} seconds..."
        sleep $WAIT_TIME
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "⚠️  Migrations failed after $MAX_RETRIES attempts, starting server anyway..."
fi

# Collect static files if not already done
python manage.py collectstatic --noinput --clear 2>&1 | grep -v "^Copying\|^Creating"

# Start the server
echo "Starting Gunicorn server..."
exec gunicorn clinic_management.wsgi:application --bind 0.0.0.0:10000 --timeout 120
