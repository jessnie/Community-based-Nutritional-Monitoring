from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test


def admin_check(user):
    return user.is_superuser


@user_passes_test(admin_check, login_url='login')
def resident_list(request):
    return redirect('resident_list')