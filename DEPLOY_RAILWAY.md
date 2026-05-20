Deploying clinic_manage to Railway

This document describes a minimal, reproducible deployment of the Django app to Railway and how to configure Sendinblue for transactional email.

1) Prepare your repo
- Push your current repo to GitHub.
- Ensure `requirements.txt` contains `django-anymail` (already added).
- Ensure you have a `Procfile` with the web start command (already present).

2) Create a Railway project
- Sign in to Railway (https://railway.app) and create a new project.
- Connect your GitHub repository.
- Set the Railway deploy branch (e.g., `main`).

3) Add environment variables
In your Railway project, open the "Variables" tab and set the following (use your real values):

- `SECRET_KEY` = (your Django secret key)
- `DEBUG` = `false`
- `DATABASE_URL` = (Railway Postgres connection URL) OR add a PostgreSQL plugin in Railway and use the provided URL
- `EMAIL_BACKEND` = `anymail.backends.sendinblue.EmailBackend`
- `SENDINBLUE_API_KEY` = (your Sendinblue API key)
- `DEFAULT_FROM_EMAIL` = `noreply@yourdomain.com`
- `PUBLIC_BASE_URL` = `https://<your-railway-domain-or-custom-domain>`

Optional (SMTP fallback):
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`

4) Build and start command
- Railway should auto-detect a Python project and install dependencies from `requirements.txt`.
- The Procfile `web: gunicorn clinic_management.wsgi --log-file -` will be used to start Gunicorn.

5) Database migrations & static files
- After deploy, run a one-off command in Railway console or add a release step if supported:

```
python manage.py migrate
python manage.py collectstatic --noinput
```

6) Configure domain and DNS (if you own a domain)
- Add your custom domain via Railway settings.
- Point your domain's A / CNAME records to Railway as instructed.

7) Sendinblue setup (SMTP/API & deliverability)
- Sign up at https://app.sendinblue.com
- Get your API key: Settings → SMTP & API → Create a new API key.
- In Sendinblue, verify your sending domain (recommended) to enable SPF/DKIM support.

DNS records (example placeholders; follow Sendinblue's UI for exact values):
- SPF TXT: `v=spf1 include:_spf.sendinblue.com ~all`
- DKIM TXT: (Sendinblue will show the DKIM selector and value; add the TXT record as provided)
- Optionally add DMARC TXT: `v=DMARC1; p=none; rua=mailto:postmaster@yourdomain.com`

8) Test email from Railway
- In Railway console, run:

```
python manage.py send_test_email you@yourdomain.com
```

- If Anymail reports success, check the inbox for the email. If it fails, check Railway logs for the error message. Common issues:
  - Missing or invalid `SENDINBLUE_API_KEY`
  - Domain not verified causing delivery or bounce
  - DNS propagation delays for SPF/DKIM

9) Troubleshooting
- View app logs and HTTP responses in Railway's Logs tab.
- If you see `AnymailAPIError` or similar, copy the error text and we can debug it.

10) Security and production tips
- Always set `DEBUG=false` in production.
- Add your domain to `ALLOWED_HOSTS` or set `ALLOWED_HOSTS` env var accordingly.
- Use secure cookies and HSTS (settings already include these when `DEBUG` is false).

If you want, I can also:
- Add a GitHub Actions workflow for deploy automation.
- Add a `release` step to run migrations automatically if you're using a host that supports release phases.

