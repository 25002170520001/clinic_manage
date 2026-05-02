"""
ASGI config for clinic_management project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clinic_management.settings")
# Auto-load .env for deployment/local
try:
    import dotenv
    dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

application = get_asgi_application()
