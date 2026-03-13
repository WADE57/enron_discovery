"""
URL configuration for enron_discovery project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
<<<<<<< HEAD
from polls.views import hello_world  # Import the hello_world view
=======
# from core.views import hello_world  # Import the hello_world view
>>>>>>> 642bc81fb4831d9d9e50e6bef85aac49e56e2930

# urlpatterns = [
#     path('admin/', admin.site.urls),
# ]
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  # Doit pointer vers core/urls.py
]
