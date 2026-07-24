from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q

from residents.models import Resident


def admin_check(user):
    return user.is_superuser


@user_passes_test(admin_check, login_url='login')
def resident_list(request):

    search = request.GET.get("search", "")

    residents = Resident.objects.all()

    if search:
        residents = residents.filter(
            Q(resident_id__icontains=search) |
            Q(first_name__icontains=search) |
            Q(middle_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(address__icontains=search)
        )

    paginator = Paginator(residents.order_by("last_name"), 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search": search,
    }

    return render(
        request,
        "admin_residents/resident_list.html",
        context
    )