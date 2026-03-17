# from django.urls import path
# from . import views

# urlpatterns = [
#     path('', views.email_list, name='email_list'),
# ]

from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("search/", views.search_emails, name="search_emails"),
    path("threads/<int:email_id>/", views.thread_detail, name="thread_detail"),
]