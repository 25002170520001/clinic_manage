"""
Django settings for clinic_management project.
"""

import os
from pathlib import Path
from datetime import timedelta

import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Helpers
def _env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name, default=""):
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_str(name, default=""):
    raw = os.getenv(name, default)
    if raw is None:
        return default
    return raw.strip().strip('"').strip("'")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = _env_str("SECRET_KEY", "django-insecure-dev-only-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _env_bool("DEBUG", default=True)

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS", "")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    # Local apps
    "accounts",
    "doctors",
    "appointments",
    "token_queue",
    "billing",
]

# Third-party email integration
INSTALLED_APPS = INSTALLED_APPS + ["anymail"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "clinic_management.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.device_context",
            ],
        },
    },
]

WSGI_APPLICATION = "clinic_management.wsgi.application"

# Database
DATABASE_URL = _env_str("DATABASE_URL", "")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    if not DEBUG:
        raise RuntimeError(
            "DATABASE_URL is required in production. Connect a persistent PostgreSQL database instead of using SQLite."
        )
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Login URL for Django admin
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Email (SMTP) - Configure these environment variables in production/local as needed:
# EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD,
# EMAIL_USE_TLS, EMAIL_USE_SSL, DEFAULT_FROM_EMAIL

# --- EMAIL CONFIGURATION (Anymail + provider-agnostic) ---
# Use console backend by default in DEBUG, otherwise prefer Anymail Sendinblue backend
_DEFAULT_EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else (
        "django.core.mail.backends.smtp.EmailBackend"
        if os.getenv("EMAIL_HOST_USER") and os.getenv("EMAIL_HOST_PASSWORD")
        else "django.core.mail.backends.console.EmailBackend"
    )
)
EMAIL_BACKEND = _env_str("EMAIL_BACKEND", _DEFAULT_EMAIL_BACKEND)

# Legacy SMTP fallbacks (still read from env if provided)
EMAIL_HOST = _env_str("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = _env_str("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = _env_str("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = _env_bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))
DEFAULT_FROM_EMAIL = _env_str("DEFAULT_FROM_EMAIL", "noreply@clinicmanage.local")

# Validate email configuration and provide warnings
# Configure Anymail (Sendinblue) from environment
ANYMAIL = {
    "SENDINBLUE_API_KEY": os.getenv("SENDINBLUE_API_KEY", ""),
    # Optional: override the API base URL
    "SENDINBLUE_API_URL": os.getenv("SENDINBLUE_API_URL", "https://api.sendinblue.com/v3/"),
}

if EMAIL_BACKEND.endswith("sendinblue.EmailBackend") and not ANYMAIL.get("SENDINBLUE_API_KEY"):
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(
        "Anymail Sendinblue backend selected but SENDINBLUE_API_KEY is not set. Emails will fail until configured."
    )

if EMAIL_BACKEND.endswith("smtp.EmailBackend") and (not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD):
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(
        "Email SMTP is not properly configured. EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is empty. "
        "Emails will not be sent until properly configured."
    )

    if DEBUG and not EMAIL_HOST_USER and not EMAIL_HOST_PASSWORD:
        EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Outbound notification integration (SMS/WhatsApp + secure document links)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
DOCUMENT_LINK_EXPIRY_SECONDS = int(os.getenv("DOCUMENT_LINK_EXPIRY_SECONDS", "86400"))
SMS_API_URL = os.getenv("SMS_API_URL", "")
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "")
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")

# Test email
def send_test_email():
    from django.core.mail import send_mail

    send_mail(
        subject="Test email",
        message="This is a test email.",
        from_email=DEFAULT_FROM_EMAIL,
        recipient_list=["test@example.com"],
    )

if __name__ == "__main__":
    send_test_email()


# Logging: ensure exceptions and errors are written to stdout so host logs capture tracebacks.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        }
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}
