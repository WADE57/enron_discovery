from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchQuery, SearchRank
from .models import Email, Employee

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

    # Agrégation par mois
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
        "total_emails": total_emails,
        "total_employees": total_employees,
        "emails_per_month": emails_per_month,
        "top_senders": top_senders,
    }
    return render(request, "dashboard.html", context)
<<<<<<< HEAD
=======

def home(request):
    return render(request, "home.html")

def conversations(request):
    return render(request, "conversation.html")

def expediteurs(request):
    return render(request, "expediteur.html")

def stats(request):
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
    return render(request, "stats.html", context)
>>>>>>> 2709479911b1ba492ac305d2c36c1d75ba4a1840

# --- Recherche avancée (FTS PostgreSQL) ---
def search_emails(request):
    q = request.GET.get("q", "").strip()
    sender = request.GET.get("sender", "").strip()
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    qs = Email.objects.select_related("from_employee").all()

    # Full Text Search si mot-clé présent
    if q:
        query = SearchQuery(q)
        qs = qs.annotate(rank=SearchRank("search_vector", query))\
               .filter(rank__gte=0.01)\
               .order_by("-rank", "-date")
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

# --- Détail d'un thread (conversation) ---
def _collect_descendants(email_obj, collected):
    """Récupère récursivement toutes les réponses."""
    children = list(email_obj.replies.select_related("from_employee").all().order_by("date", "id"))
    for child in children:
        collected.append(child)
        _collect_descendants(child, collected)

def thread_detail(request, email_id):
    selected = get_object_or_404(Email.objects.select_related("from_employee"), id=email_id)

    # Remonter à la racine du thread
    root = selected
    while root.in_reply_to_id:
        root = root.in_reply_to

    # Collecter tous les descendants
    descendants = []
    _collect_descendants(root, descendants)
    conversation = [root] + descendants

    context = {
        "selected": selected,
        "root": root,
        "conversation": conversation,
    }
    return render(request, "thread_detail.html", context)

# --- Graphe d'influence (optionnel mais demandé) ---
def influence_graph(request):
    user_email = request.GET.get("user", "").strip()
    connections = (
        Email.objects.exclude(to_employees__isnull=True)
        .values("from_employee__email", "to_employees__email")
        .annotate(total=Count("id"))
    )
    if user_email:
        connections = connections.filter(
            Q(from_employee__email__icontains=user_email) |
            Q(to_employees__email__icontains=user_email)
        )
    connections = connections.order_by("-total")[:100]

    context = {
        "connections": connections,
        "user_email": user_email,
    }
    return render(request, "influence.html", context)

# --- (Optionnel) Liste simple de tous les emails ---
def email_list(request):
    emails_list = Email.objects.select_related("from_employee").all().order_by("-date")
    paginator = Paginator(emails_list, 50)
    page_number = request.GET.get("page")
    emails = paginator.get_page(page_number)

    stats = {
        "total_emails": Email.objects.count(),
        "total_employees": Employee.objects.count(),
    }
<<<<<<< HEAD
    context = {
        "emails": emails,
        "stats": stats,
    }
    return render(request, "email_list.html", context)
=======
    return render(request, "thread_detail.html", context)
>>>>>>> 2709479911b1ba492ac305d2c36c1d75ba4a1840
