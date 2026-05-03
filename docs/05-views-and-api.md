# Phase 5: Views, API Endpoints, and HTMX Components

## Goal
Build Django views and REST API endpoints for serving layoff data, with HTMX-powered auto-refreshing components.

## URL Structure

| URL Pattern | View | Method | Description |
|-------------|------|--------|-------------|
| `/` | `HomePageView` | GET | Main page: recent disclosures + news + community |
| `/dashboard/` | `DashboardView` | GET | Charts and statistics |
| `/layoffs/{id}/` | `LayoffDetailView` | GET | Single layoff event detail |
| `/api/layoffs/` | `LayoffEventViewSet` | GET,POST,... | Full CRUD API |
| `/api/news/` | `NewsArticleViewSet` | GET | News articles API |
| `/api/stats/` | `StatsView` | GET | Aggregate statistics |
| `/htmx/recent-disclosures/` | `htmx_recent_disclosures` | GET | Table partial (HTMX) |
| `/htmx/tech-news/` | `htmx_tech_news` | GET | News cards partial (HTMX) |
| `/htmx/stats-summary/` | `htmx_stats_summary` | GET | Stats panel partial (HTMX) |

## Views

### 5.1 HomePageView (TemplateView)
- Context includes:
  - `recent_layoffs`: Latest 20 LayoffEvents
  - `news_articles`: Latest 8 NewsArticles
  - `community_stats`: Member count, thread count
  - `total_laid_off`: Sum of all known layoffs
  - `stats`: Aggregate stats object
- Renders `home.html`

### 5.2 DashboardView (TemplateView)
- Context includes:
  - `layoffs_by_month`: Grouped data for line chart
  - `layoffs_by_industry`: Grouped data for pie chart
  - `top_companies`: Top 10 by total layoffs
  - `layoffs_trend`: 12-month rolling trend
- Renders `dashboard.html` with Chart.js

### 5.3 HTMX Partial Views
Each partial returns a rendered HTML fragment:
```python
@require_http_methods(['GET'])
def htmx_recent_disclosures(request):
    layoffs = LayoffEvent.objects.filter(is_verified=True)[:15]
    return render(request, 'components/recent_table.html', {'layoffs': layoffs})
```

With HTMX auto-refresh:
```html
<div hx-get="/htmx/recent-disclosures/"
     hx-trigger="every 60s"
     hx-swap="outerHTML">
  {% include "components/recent_table.html" %}
</div>
```

### 5.4 REST API (Django REST Framework)
- `LayoffEventViewSet`:
  - Ordering: `-date_reported`
  - Filtering: `company`, `industry`, `is_ai_related`, `date_reported__gte`
  - Search: `company`, `notes`
  - Pagination: 50 per page

- `StatsView` (APIView):
  - Returns JSON with:
    - `total_companies`, `total_laid_off`
    - `avg_percentage`
    - `most_recent_date`
    - `by_industry`: [{industry, count, total}]
    - `by_month`: [{month, count, total}]

## Templates

### Home Page Layout
```
┌─────────────────────────────────────────────────────────┐
│  Sticky Header (logo + nav + theme toggle + auth)       │
├────────────────────────────────┬────────────────────────┤
│  Recent Disclosures            │  Community Sidebar     │
│  ─────────────────────────     │  ──────────────        │
│  [Table: Company, Jobs, %,    │  • 8 members           │
│          Source, Date]         │  • 7 threads           │
│                                │  • Latest discussions  │
│  Auto-refreshes every 60s     │                        │
├────────────────────────────────┴────────────────────────┤
│  Relevant Tech News                                     │
│  ────────────────────                                   │
│  [Card grid: thumbnail, source, headline, snippet]      │
│  Auto-refreshes every 120s                              │
└─────────────────────────────────────────────────────────┘
```
