from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def staff_required(view_function):
    @login_required(login_url='login')
    @wraps(view_function)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        return view_function(request, *args, **kwargs)

    return wrapped_view