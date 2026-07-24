from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404

from .forms import UserForm


def admin_check(user):
    return user.is_superuser


@user_passes_test(admin_check, login_url="login")
def user_list(request):

    users = User.objects.all().order_by("username")

    return render(
        request,
        "user_management/user_list.html",
        {
            "users": users
        }
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

    user = get_object_or_404(User, pk=pk)

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
            "title": "Edit User"
        }
    )


@user_passes_test(admin_check, login_url="login")
def delete_user(request, pk):

    user = get_object_or_404(User, pk=pk)

    if request.method == "POST":

        user.delete()

        return redirect("user_list")

    return render(
        request,
        "user_management/user_delete.html",
        {
            "user": user
        }
    )