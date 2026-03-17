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
]