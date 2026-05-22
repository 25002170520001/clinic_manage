Deployment notes — Fly.io and Railway

This project is configured to run under Docker. The repository includes a `Dockerfile` and `fly.toml` to help deploy to Fly.io, and can also be deployed to Railway using their Docker deploy or buildpacks.

Fly.io (quick steps):

1. Install Fly CLI and login: `flyctl auth login`
2. Create or select an app: `flyctl apps create clinic-manage-fly` (or run `fly launch`)
3. Set secrets (required):

```bash
flyctl secrets set SECRET_KEY='your-secret' DEBUG=0 DATABASE_URL='postgres://...' \
  EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend' EMAIL_HOST='smtp.gmail.com' \
  EMAIL_PORT=587 EMAIL_HOST_USER='you@example.com' EMAIL_HOST_PASSWORD='app-password' EMAIL_USE_TLS=1
```

4. Deploy (runs `release_command` which migrates):
```bash
flyctl deploy
```
5. (Optional) Add a custom domain in the Fly dashboard and point your DNS records to Fly. If you don't have a custom domain, Fly will provide a hostname for the app.

Railway (quick steps):

1. Install Railway CLI: `npm i -g railway`
2. Create a project or connect GitHub repo in the Railway dashboard.
3. Use Railway's env UI or CLI to add env vars listed above.
4. If using Docker, Railway will build the included `Dockerfile`. Otherwise use Python buildpack.
5. Run migrations via a one-off job or in a startup command: `python manage.py migrate --noinput`.
6. Railway will provide a public URL for your service (for this project: `web-production-1add8.up.railway.app`). If you have a custom domain you may add it in Railway and follow the DNS instructions; otherwise the Railway URL works without additional DNS setup.

Important:
- Keep `DATABASE_URL` and SMTP env vars secret. Do not commit them to the repo.
- Ensure `DEBUG=0` and `ALLOWED_HOSTS` updated for your production hostname (e.g. `web-production-1add8.up.railway.app`).
- For Fly, use `flyctl secrets` (they are encrypted). For Railway, use the environment variables UI.

If you want, I can continue and perform the deployment to Fly.io or Railway now — I will need CLI access (logged-in session) or your confirmation to proceed interactively.
