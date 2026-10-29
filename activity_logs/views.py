from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import ActivityLog


@login_required(login_url='login')
def activity_logs(request):

    logs = ActivityLog.objects.select_related(
        'user'
    ).all()
    paginator = Paginator(logs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'total_logs': paginator.count,
    }

    return render(

        request,

        'activity_logs/dashboard.html',

        context

    )