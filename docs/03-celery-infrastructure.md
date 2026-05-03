# Phase 3: Celery / Redis Task Infrastructure

## Goal
Set up Celery with Redis broker, configure periodic tasks via Celery Beat, and build the task pipeline for data ingestion.

## Architecture

```
Celery Beat ──► Schedule ──► Celery Worker ──► Task Execution ──► DB
                  │
            (reads schedule
             from django_celery_beat
             or code-based schedule)
```

## Steps

### 3.1 Celery App Config (`layoffs_tracker/celery.py`)

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'layoffs_tracker.settings')

app = Celery('layoffs_tracker')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

### 3.2 Settings Config

```python
# settings.py
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

### 3.3 Periodic Task Schedule

| Task | Interval | Description |
|------|----------|-------------|
| `collect_rss_sources` | Every 15 min | Poll all active RSS feeds |
| `collect_web_sources` | Every 30 min | Scrape known layoff tracking websites |
| `llm_research_task` | Every 4 hours | LLM-powered deep research for new layoffs |
| `enrich_pending_events` | Every hour | LLM enrichment (industry, AI-tag, confidence) |
| `collect_news_articles` | Every 30 min | Gather general tech news |
| `cleanup_stale_data` | Daily at 3am | Remove duplicate/expired entries |

### 3.4 Task Pipeline

```
[Beat Fires]
     │
     ▼
[Dispatcher Task]
     │
     ├──► [RSS Collector]    feedparser → extract → normalize → dedup → save
     ├──► [Web Scraper]      requests + bs4 → parse → extract → save
     ├──► [LLM Research]     OpenAI/DeepSeek API → parse JSON → validate → save
     └──► [Enrichment]       Take unverified events → LLM enrich → update
```

### 3.5 Running Services

```bash
# Terminal 1: Celery Worker
celery -A layoffs_tracker worker -l info

# Terminal 2: Celery Beat
celery -A layoffs_tracker beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Or combined (dev only):
celery -A layoffs_tracker worker -B -l info
```

### 3.6 Error Handling & Retries
- Each task has `max_retries=3`, `default_retry_delay=300` (5 min)
- Failed tasks logged to `scraper.models.ScrapeLog`
- Circuit breaker: if a DataSource fails 5+ consecutive times, auto-deactivate it

### 3.7 Monitoring
- Flower for Celery monitoring (optional)
- django-celery-beat admin UI for managing schedules
- Custom admin view showing task execution history
