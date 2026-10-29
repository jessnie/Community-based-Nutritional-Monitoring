from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
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

    if request.method == "POST":

        form = UserForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect("user_list")

    else:

        form = UserForm()

    return render(
        request,
        "user_management/user_form.html",
        {
            "form": form,
            "title": "Add User"
        }
    )


@user_passes_test(admin_check, login_url="login")
def edit_user(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)

    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("user_list")
    else:
        form = UserForm(instance=user)

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