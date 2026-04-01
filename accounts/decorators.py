from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("web-login")
            user_role = "admin" if request.user.is_superuser else request.user.role
            if user_role not in roles:
                messages.error(request, "You do not have permission to access this page.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
