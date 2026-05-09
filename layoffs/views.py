from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils.timezone import now
from django.views.generic import DetailView, TemplateView
from rest_framework import viewsets, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import LayoffEvent
from .serializers import LayoffEventSerializer, LayoffStatsSerializer

PAGE_SIZE = 10

SORT_FIELDS = {
    'company': 'company',
    'headcount': 'headcount',
    'percentage': 'percentage',
    'source': 'source_name',
    'date': 'date_reported',
}

DEFAULT_SORT = 'date'
DEFAULT_DIR = 'desc'


def _apply_sorting(qs, sort, dir):
    """Apply sort field and direction to a queryset, with validation."""
    field = SORT_FIELDS.get(sort, SORT_FIELDS[DEFAULT_SORT])
    if dir == 'desc':
        field = f'-{field}'
    return qs.order_by(field)


# ── Django Views ──

class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort = self.request.GET.get('sort', DEFAULT_SORT)
        dir = self.request.GET.get('dir', DEFAULT_DIR)
        qs = _apply_sorting(LayoffEvent.objects.all(), sort, dir)
        paginator = Paginator(qs, PAGE_SIZE)
        page = paginator.get_page(1)
        context['layoffs'] = page.object_list
        context['page_obj'] = page
        context['paginator'] = paginator
        context['current_sort'] = sort
        context['current_dir'] = dir
        context['total_laid_off'] = LayoffEvent.objects.aggregate(
            total=Sum('headcount')
        )['total'] or 0
        context['total_companies'] = LayoffEvent.objects.values('company').distinct().count()
        from news.models import NewsArticle
        context['news_articles'] = NewsArticle.objects.all()[:8]
        return context


class DashboardView(TemplateView):
    template_name = 'dashboard.html'


class LayoffDetailView(DetailView):
    model = LayoffEvent
    template_name = 'layoff_detail.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_laid_off'] = LayoffEvent.objects.aggregate(
            total=Sum('headcount')
        )['total'] or 0
        context['total_companies'] = LayoffEvent.objects.values('company').distinct().count()
        return context


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
    page_num = request.GET.get('page', 1)
    sort = request.GET.get('sort', DEFAULT_SORT)
    dir = request.GET.get('dir', DEFAULT_DIR)
    qs = _apply_sorting(LayoffEvent.objects.all(), sort, dir)
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(page_num)
    return render(request, 'components/recent_table.html', {
        'layoffs': page.object_list,
        'page_obj': page,
        'paginator': paginator,
        'current_sort': sort,
        'current_dir': dir,
    })


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
