from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.contrib.postgres.search import SearchQuery, SearchRank
from .models import Email, Employee

MIN_VALID_YEAR = 1990
MAX_VALID_YEAR = 2010
SEARCH_PAGE_SIZE = 20


def _paginate_without_count(qs, page_str, per_page=SEARCH_PAGE_SIZE):
    try:
        page = int(page_str or 1)
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1

    start = (page - 1) * per_page
    rows = list(qs[start : start + per_page + 1])
    has_next = len(rows) > per_page
    emails = rows[:per_page]

    return {
        "emails": emails,
        "current_count": len(emails),
        "current_page": page,
        "has_previous": page > 1,
        "previous_page": page - 1,
        "has_next": has_next,
        "next_page": page + 1,
    }


def _result_label(pagination, per_page=SEARCH_PAGE_SIZE):
    shown_until = (pagination["current_page"] - 1) * per_page + pagination["current_count"]
    if pagination["has_next"]:
        return f"{shown_until}+"
    return shown_until

# --- Accueil ---
def home(request):
    total_emails = Email.objects.count()
    total_employees = Employee.objects.count()
    top_senders = (
        Email.objects.values("from_employee__email")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )
    context = {
        "total_emails": total_emails,
        "total_employees": total_employees,
        "top_senders": top_senders,
    }
    return render(request, "home.html", context)

# --- Dashboard avec graphique ---
def dashboard(request):
    total_emails = Email.objects.count()
    total_employees = Employee.objects.count()

    emails_per_month = (
        Email.objects.exclude(date__isnull=True)
        .filter(date__year__gte=MIN_VALID_YEAR, date__year__lte=MAX_VALID_YEAR)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    monthly_rows = list(emails_per_month)
    chart_labels = [
        row["month"].strftime("%b %Y") if row.get("month") else ""
        for row in monthly_rows
    ]
    chart_values = [row["total"] for row in monthly_rows]

    top_senders = (
        Email.objects.values("from_employee__email")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    context = {
        "total_emails": total_emails,
        "total_employees": total_employees,
        "emails_per_month": emails_per_month,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "top_senders": top_senders,
    }
    return render(request, "dashboard.html", context)

# --- Recherche avancée (FTS PostgreSQL) ---
def search_emails(request):
    q = request.GET.get("q", "").strip()
    sender = request.GET.get("sender", "").strip()
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    has_filters = any([q, sender, date_from, date_to])

    qs = Email.objects.select_related("from_employee").all()

    if sender:
        qs = qs.filter(from_employee__email__icontains=sender)
    if date_from:
        qs = qs.filter(date__date__gte=date_from)
    if date_to:
        qs = qs.filter(date__date__lte=date_to)

    if q:
        query = SearchQuery(q)
        qs = qs.filter(search_vector=query)\
               .annotate(rank=SearchRank("search_vector", query))\
               .order_by("-rank", "-date")
    else:
        qs = qs.order_by("-date")

    pagination = _paginate_without_count(qs, request.GET.get("page"))

    context = {
        "emails": pagination["emails"],
        "current_page": pagination["current_page"],
        "has_previous": pagination["has_previous"],
        "previous_page": pagination["previous_page"],
        "has_next": pagination["has_next"],
        "next_page": pagination["next_page"],
        "q": q,
        "sender": sender,
        "date_from": date_from,
        "date_to": date_to,
        "total_results": _result_label(pagination),
        "search_hint": "Affichage de tous les emails (pagine). Ajoutez des filtres pour affiner." if not has_filters else "",
        "enable_pagination": True,
    }
    return render(request, "search.html", context)

# --- Détail d'un thread (conversation) ---
def _collect_descendants(email_obj, collected):
    children = list(email_obj.replies.select_related("from_employee").all().order_by("date", "id"))
    for child in children:
        collected.append(child)
        _collect_descendants(child, collected)

def thread_detail(request, email_id):
    selected = get_object_or_404(Email.objects.select_related("from_employee"), id=email_id)

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

# --- Graphe d'influence ---
from django.db.models import Count, Q

def influence_graph(request):
    user_email = request.GET.get("user", "").strip()

    connections = (
        Email.objects
        .values('from_employee__email', 'to_employees__email')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    if user_email:
        connections = connections.filter(
            Q(from_employee__email__icontains=user_email) |
            Q(to_employees__email__icontains=user_email)
        )

    connections = connections[:100]

    context = {
        "connections": connections,
        "user_email": user_email,
    }
    return render(request, "influence.html", context)

# --- Liste simple de tous les emails ---
def email_list(request):
    emails_list = Email.objects.select_related("from_employee").all().order_by("-date")
    paginator = Paginator(emails_list, 50)
    page_number = request.GET.get("page")
    emails = paginator.get_page(page_number)

    stats = {
        "total_emails": Email.objects.count(),
        "total_employees": Employee.objects.count(),
    }
    context = {
        "emails": emails,
        "stats": stats,
    }
    return render(request, "email_list.html", context)  # 