"""
URL configuration for layoffs_tracker project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('layoffs.urls')),
    path('api/', include('news.urls')),
    path('', include('layoffs.urls')),
]
