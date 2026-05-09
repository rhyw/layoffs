from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

# DRF Router
router = DefaultRouter()
router.register(r'layoffs', views.LayoffEventViewSet, basename='layoff')

urlpatterns = [
    # Django views
    path('', views.HomePageView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('layoffs/<int:pk>/', views.LayoffDetailView.as_view(), name='layoff-detail'),

    # DRF API
    path('stats/', views.layoff_stats, name='api-stats'),

    # HTMX partials
    path('htmx/recent-disclosures/', views.htmx_recent_disclosures, name='htmx-disclosures'),
    path('htmx/tech-news/', views.htmx_tech_news, name='htmx-news'),
    path('htmx/stats-summary/', views.htmx_stats_summary, name='htmx-stats'),
] + router.urls
