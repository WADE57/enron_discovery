from django.urls import path
from . import views

urlpatterns = [
    path('', views.email_list, name='email_list'),
]