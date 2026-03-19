from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('stats/', views.stats, name='stats'),
    path('search/', views.search_emails, name='search_emails'),
    path('conversations/', views.conversations, name='conversations'),
    path('threads/<int:email_id>/', views.thread_detail, name='thread_detail'),
    path('influence/', views.influence_graph, name='influence'),
    path('expediteurs/', views.expediteurs, name='expediteurs'),
]