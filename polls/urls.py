from django.urls import path
from . import views

app_name = 'enron'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('search/', views.search_emails, name='search_emails'),
    path('thread/<int:email_id>/', views.thread_detail, name='thread_detail'),
    path('influence/', views.influence_graph, name='influence_graph'),
    path('emails/', views.email_list, name='email_list'),
]