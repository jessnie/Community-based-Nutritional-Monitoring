from activity_logs.utils import log_activity
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect


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