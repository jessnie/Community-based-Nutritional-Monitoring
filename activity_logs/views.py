from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import ActivityLog


@login_required(login_url='login')
def activity_logs(request):

    logs = ActivityLog.objects.select_related(
        'user'
    ).all()

    context = {

        'logs': logs,

        'total_logs': logs.count(),

    }

    return render(

        request,

        'activity_logs/dashboard.html',

        context

    )