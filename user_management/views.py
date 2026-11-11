from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect

from .forms import UserForm


def admin_check(user):
    return user.is_superuser


@user_passes_test(admin_check, login_url="login")
def user_list(request):
    return render(
        request,
        "user_management/user_list.html",
        {
            "users": get_user_model().objects.order_by("username"),
            "admin_count": get_user_model().objects.filter(
                is_superuser=True
            ).count(),
        },
    )


@user_passes_test(admin_check, login_url="login")
def add_user(request):
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method == "POST":

        form = UserForm(request.POST)

        if form.is_valid():

            form.save()
            if is_ajax:
                return JsonResponse({"success": True})

            return redirect("user_list")

    else:

        form = UserForm()

    if is_ajax:
        return render(
            request,
            "user_management/_user_form_fields.html",
            {
                "form": form,
                "is_modal": True,
            },
            status=400 if request.method == "POST" else 200,
        )

    return render(
        request,
        "user_management/user_form.html",
        {
            "form": form,
            "title": "Create User Account"
        }
    )


@user_passes_test(admin_check, login_url="login")
def edit_user(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "message": "Update successfully",
                })
            return redirect("user_list")
    else:
        form = UserForm(instance=user)

    if is_ajax:
        return render(
            request,
            "user_management/_user_form_fields.html",
            {
                "form": form,
                "is_modal": True,
            },
            status=400 if request.method == "POST" else 200,
        )

    return render(
        request,
        "user_management/user_form.html",
        {
            "form": form,
            "title": f"Edit User: {user.username}",
        },
    )


@user_passes_test(admin_check, login_url="login")
def delete_user(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)

    if user.pk == request.user.pk or (
        user.is_superuser
        and get_user_model().objects.filter(is_superuser=True).count() <= 1
    ):
        return redirect("user_list")

    if request.method == "POST":
        user.delete()
        return redirect("user_list")

    return render(
        request,
        "user_management/user_delete.html",
        {"user": user},
    )