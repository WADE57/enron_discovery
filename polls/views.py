# from django.shortcuts import render
# from django.core.paginator import Paginator
# from .models import Email, Employee

# def email_list(request):
#     # Récupère tous les emails triés par date
#     emails_list = Email.objects.all().select_related('from_employee').order_by('-date')
    
#     # Pagination : 20 emails par page
#     paginator = Paginator(emails_list, 20)
#     page_number = request.GET.get('page')
#     emails = paginator.get_page(page_number)
    
#     # Statistiques
#     stats = {
#         'total_emails': Email.objects.count(),
#         'total_employees': Employee.objects.count(),
#     }
    
#     return render(request, 'email_list.html', {
#         'emails': emails,
#         'stats': stats
#     })

from django.shortcuts import render
from django.db.models import Count
from django.db.models.functions import TruncMonth
from .models import Email, Employee

def dashboard(request):
    emails_per_month = (
        Email.objects.exclude(date__isnull=True)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    top_senders = (
        Email.objects.values("from_employee__email")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    context = {
        "total_emails": Email.objects.count(),
        "total_employees": Employee.objects.count(),
        "emails_per_month": emails_per_month,
        "top_senders": top_senders,
    }
    return render(request, "dashboard.html", context)