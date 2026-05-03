from datetime import timedelta

from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils.timezone import now
from django.views.generic import TemplateView
from rest_framework import viewsets, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import LayoffEvent
from .serializers import LayoffEventSerializer, LayoffStatsSerializer


# ── Django Views ──

class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recent = LayoffEvent.objects.all()[:20]
        context['layoffs'] = recent
        context['total_laid_off'] = LayoffEvent.objects.aggregate(
            total=Sum('headcount')
        )['total'] or 0
        context['total_companies'] = LayoffEvent.objects.values('company').distinct().count()
        return context


class DashboardView(TemplateView):
    template_name = 'dashboard.html'


# ── DRF API Views ──

class LayoffEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LayoffEvent.objects.all()
    serializer_class = LayoffEventSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['company', 'notes']
    ordering_fields = ['date_reported', 'headcount', 'company']
    ordering = ['-date_reported']

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by verified status
        verified = self.request.query_params.get('verified')
        if verified is not None:
            qs = qs.filter(is_verified=verified.lower() == 'true')
        # Filter by AI-related
        ai = self.request.query_params.get('ai')
        if ai is not None:
            qs = qs.filter(is_ai_related=ai.lower() == 'true')
        # Filter by industry
        industry = self.request.query_params.get('industry')
        if industry:
            qs = qs.filter(industry__iexact=industry)
        # Date range filter
        days = self.request.query_params.get('days')
        if days:
            try:
                qs = qs.filter(date_reported__gte=now().date() - timedelta(days=int(days)))
            except ValueError:
                pass
        return qs


@api_view(['GET'])
def layoff_stats(request):
    """Aggregate statistics for the dashboard."""
    total_laid_off = LayoffEvent.objects.aggregate(total=Sum('headcount'))['total'] or 0
    total_companies = LayoffEvent.objects.values('company').distinct().count()
    avg_pct = LayoffEvent.objects.filter(percentage__isnull=False).aggregate(
        avg=Avg('percentage')
    )['avg'] or 0.0
    most_recent = LayoffEvent.objects.order_by('-date_reported').first()

    # By industry
    by_industry = list(
        LayoffEvent.objects.values('industry')
        .annotate(count=Count('id'), total=Sum('headcount'))
        .order_by('-total')
    )

    # By month (last 12 months)
    twelve_months_ago = now().date() - timedelta(days=365)
    by_month = list(
        LayoffEvent.objects.filter(date_reported__gte=twelve_months_ago)
        .annotate(month=TruncMonth('date_reported'))
        .values('month')
        .annotate(count=Count('id'), total=Sum('headcount'))
        .order_by('month')
    )

    data = {
        'total_companies': total_companies,
        'total_laid_off': total_laid_off,
        'avg_percentage': round(float(avg_pct), 2),
        'most_recent_date': most_recent.date_reported if most_recent else None,
        'by_industry': by_industry,
        'by_month': by_month,
    }
    return Response(data)


# ── HTMX Partial Views ──

def htmx_recent_disclosures(request):
    layoffs = LayoffEvent.objects.all()[:20]
    return render(request, 'components/recent_table.html', {'layoffs': layoffs})


def htmx_tech_news(request):
    from news.models import NewsArticle
    articles = NewsArticle.objects.all()[:8]
    return render(request, 'components/news_cards.html', {'news_articles': articles})


def htmx_stats_summary(request):
    from django.db.models import Sum
    total_laid_off = LayoffEvent.objects.aggregate(total=Sum('headcount'))['total'] or 0
    total_companies = LayoffEvent.objects.values('company').distinct().count()
    recent = LayoffEvent.objects.order_by('-date_reported').first()
    context = {
        'total_laid_off': total_laid_off,
        'total_companies': total_companies,
        'most_recent': recent.date_reported if recent else None,
    }
    return render(request, 'components/stats_panel.html', context)
