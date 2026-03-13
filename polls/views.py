from django.shortcuts import render
from django.core.paginator import Paginator
from .models import Email, Employee

def email_list(request):
    # Récupère tous les emails triés par date
    emails_list = Email.objects.all().select_related('from_employee').order_by('-date')
    
    # Pagination : 20 emails par page
    paginator = Paginator(emails_list, 20)
    page_number = request.GET.get('page')
    emails = paginator.get_page(page_number)
    
    # Statistiques
    stats = {
        'total_emails': Email.objects.count(),
        'total_employees': Employee.objects.count(),
    }
    
    return render(request, 'email_list.html', {
        'emails': emails,
        'stats': stats
    })