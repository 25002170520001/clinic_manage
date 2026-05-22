Deployment Guide (Auto Deploy)

Goal
- Every push to the main branch updates your live website automatically.

Recommended Stack
- GitHub for source control
- Render for hosting (web service + PostgreSQL)

What Is Already Added In This Repo
- render.yaml for Render infrastructure and auto-deploy
- Procfile for Gunicorn startup
- .github/workflows/ci.yml for automatic checks and tests on push/PR
- Production-ready Django settings using environment variables

One-Time Setup
1. Push this repository to GitHub.
2. In Render, choose New + Blueprint and connect your GitHub repo.
3. Render will detect render.yaml and create:
   - Web service: clinic-manage
   - PostgreSQL database: clinic-manage-db
4. In Render (or your chosen host), open the web service and update:
   - `ALLOWED_HOSTS` to include the production hostname. For Railway this is typically the Railway-provided URL, e.g. `web-production-1add8.up.railway.app`.
   - `CSRF_TRUSTED_ORIGINS` to include your HTTPS domain(s), for example `https://web-production-1add8.up.railway.app`.
   - Email variables if you need outgoing email
5. Trigger first deploy.

How Auto Deploy Works
- You push code to main on GitHub.
- GitHub Actions runs checks/tests from .github/workflows/ci.yml.
- Render auto-deploys latest main commit.
- Website updates live after successful build/start.

Required Environment Variables (Production)
- SECRET_KEY
- DEBUG=0
- ALLOWED_HOSTS, for example `web-production-1add8.up.railway.app`
- CSRF_TRUSTED_ORIGINS, for example `https://web-production-1add8.up.railway.app`
- DATABASE_URL (provided by Render)

Optional Environment Variables
- EMAIL_HOST
- EMAIL_PORT
- EMAIL_HOST_USER
- EMAIL_HOST_PASSWORD
- EMAIL_USE_TLS
- EMAIL_USE_SSL
- DEFAULT_FROM_EMAIL
- PUBLIC_BASE_URL, for example `https://web-production-1add8.up.railway.app`

Local Development
- Keep DEBUG=1
- Use SQLite (default when DATABASE_URL is empty)
- Run: python manage.py runserver

Important Security Notes
- Never commit real passwords or API keys.
- Keep .env out of version control.
- Use HTTPS in production and valid host/origin values.
