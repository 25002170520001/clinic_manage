# Bind to the port Railway provides in the `PORT` env var so the platform can route traffic correctly
# Run migrations on process start (temporary) then start Gunicorn
web: sh -c "python manage.py migrate --noinput && gunicorn clinic_management.wsgi:application --bind 0.0.0.0:$PORT --log-file -"
# optional: use a release command if your host supports it to run migrations automatically
# release: python manage.py migrate --noinput
