from activity_logs.utils import log_activity
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect

from .forms import AccountSettingsForm, SystemSettingsForm
from .models import SystemSettings


@login_required(login_url='login')
def account_settings(request):
    if not request.user.is_superuser:
        messages.error(request, 'Settings are available to administrators only.')
        return redirect('dashboard')

    system_settings, _ = SystemSettings.objects.get_or_create(pk=1)
    account_form = AccountSettingsForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)
    system_form = (
        SystemSettingsForm(instance=system_settings)
        if request.user.is_superuser
        else None
    )

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'profile':
            account_form = AccountSettingsForm(
                request.POST,
                instance=request.user,
            )
            if account_form.is_valid():
                account_form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('account_settings')
        elif form_type == 'password':
            password_form = PasswordChangeForm(
                user=request.user,
                data=request.POST,
            )
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully.')
                return redirect('account_settings')
        elif form_type == 'system' and request.user.is_superuser:
            system_form = SystemSettingsForm(
                request.POST,
                instance=system_settings,
            )
            if system_form.is_valid():
                system_form.save()
                messages.success(request, 'System information updated successfully.')
                return redirect('account_settings')
        else:
            messages.error(request, 'Choose a valid settings form.')

    for field in password_form.fields.values():
        field.widget.attrs['class'] = 'form-control'

    return render(
        request,
        'accounts/settings.html',
        {
            'base_template': (
                'base_admin.html'
                if request.user.is_superuser
                else 'base_staff.html'
            ),
            'account_form': account_form,
            'password_form': password_form,
            'system_form': system_form,
        },
    )


def login_view(request):

    # If already logged in
    if request.user.is_authenticated:

        if request.user.is_superuser:
            return redirect('admin_dashboard')

        return redirect('dashboard')


    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")


        user = authenticate(
            request,
            username=username,
            password=password
        )


        if user is not None:

            login(request, user)

            log_activity(
    user,
    "Login",
    f"{user.username} logged into the system."
)


            # ============================
            # ADMIN LOGIN
            # ============================

            if user.is_superuser:

                return redirect(
                    'admin_dashboard'
                )


            # ============================
            # STAFF / NORMAL USER LOGIN
            # ============================

            else:

                return redirect(
                    'dashboard'
                )


        else:

            messages.error(
                request,
                "Invalid username or password."
            )


    return render(
        request,
        "accounts/login.html"
    )



def logout_view(request):

    if request.user.is_authenticated:

        log_activity(
            request.user,
            "Logout",
            f"{request.user.username} logged out of the system."
        )

    logout(request)

    return redirect('login')