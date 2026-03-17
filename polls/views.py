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

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.contrib.postgres.search import SearchQuery, SearchRank
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


def search_emails(request):
    q = request.GET.get("q", "").strip()
    sender = request.GET.get("sender", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    qs = Email.objects.select_related("from_employee").all()

    if q:
        query = SearchQuery(q)
        qs = qs.annotate(rank=SearchRank("search_vector", query)).filter(
            rank__gte=0.01
        ).order_by("-rank", "-date")
    else:
        qs = qs.order_by("-date")

    if sender:
        qs = qs.filter(from_employee__email__icontains=sender)

    if date_from:
        qs = qs.filter(date__date__gte=date_from)

    if date_to:
        qs = qs.filter(date__date__lte=date_to)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "q": q,
        "sender": sender,
        "date_from": date_from,
        "date_to": date_to,
        "total_results": qs.count(),
    }
    return render(request, "search.html", context)


def _collect_descendants(email_obj, collected):
    children = list(email_obj.replies.select_related("from_employee").all().order_by("date", "id"))
    for child in children:
        collected.append(child)
        _collect_descendants(child, collected)


def thread_detail(request, email_id):
    selected = get_object_or_404(Email.objects.select_related("from_employee"), id=email_id)

    # Find thread root by walking up in_reply_to.
    root = selected
    while root.in_reply_to_id:
        root = root.in_reply_to

    descendants = []
    _collect_descendants(root, descendants)
    conversation = [root] + descendants

    context = {
        "selected": selected,
        "root": root,
        "conversation": conversation,
    }
    return render(request, "thread_detail.html", context)