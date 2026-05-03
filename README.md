# layoffs ICU

A real-time layoff tracking and tech industry news platform. Built with Django, HTMX, Celery/Redis, and PostgreSQL, powered by DeepSeek LLM for automated data collection and enrichment.

## Features

- **Recent Disclosures** — Auto-refreshing table of layoff events sourced from RSS feeds and LLM-powered research
- **Tech News** — Aggregated tech news from The Verge, TechCrunch, Ars Technica, Wired
- **Dashboard** — Charts and statistics (layoffs over time, by industry, top companies)
- **REST API** — Full DRF API for layoff events and news articles
- **Dark/Light Theme** — Persisted in localStorage, dark mode by default
- **Community** — Discussion threads (forum feature, models ready for future UI)

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Browser    │◄──►│   Django     │◄──►│  PostgreSQL  │
│  (HTMX +     │    │  + DRF API   │    │              │
│   Chart.js)  │    │              │    └──────────────┘
└──────────────┘    └──────┬───────┘
                           │
                    ┌──────▼───────┐    ┌──────────────┐
                    │   Celery     │◄──►│    Redis     │
                    │   Workers    │    │              │
                    └──────┬───────┘    └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  Collectors  │
                    │  ┌─────────┐ │
                    │  │  RSS    │ │
                    │  │  Web    │ │
                    │  │  LLM    │ │
                    │  │  News   │ │
                    │  └─────────┘ │
                    └──────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Redis (for Celery task queue)
- PostgreSQL (optional — SQLite works for local dev)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/layoffs.git
cd layoffs
cp .env.example .env
```

Edit `.env` to match your environment. For local development, SQLite is the default:

```env
SECRET_KEY=django-insecure-generate-a-real-one
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
DEEPSEEK_API_KEY=sk-your-deepseek-api-key  # optional for dev
```

### 2. Create & Activate Virtual Environment

```bash
# Using venv (built-in)
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# Using uv (faster)
uv venv
source .venv/bin/activate      # macOS/Linux
```

Your prompt should now show `(.venv)` at the beginning, confirming the virtual environment is active.

### 3. Install Dependencies

```bash
# With venv activated, using pip:
pip install -r requirements.txt

# Or using uv (faster):
uv pip install -r requirements.txt
```

### 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Seed Data Sources

```bash
python manage.py seed_datasources
```

### 6. Start the App

```bash
# In terminal 1: Django dev server
python manage.py runserver

# In terminal 2: Celery worker (optional — needed for data collection)
celery -A layoffs_tracker worker -l info

# In terminal 3: Celery beat (optional — schedules periodic tasks)
celery -A layoffs_tracker beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Visit **http://localhost:8000** in your browser.

> **Note:** The app works without Celery running. You'll see the UI and manually add layoff events via the admin at `/admin/`. Celery enables automated data collection from RSS feeds and LLM sources.

## Docker (Production)

### Start the full stack

```bash
docker compose up -d --build
```

This starts 5 services: `web` (Gunicorn), `worker` (Celery), `beat` (Celery Beat), `redis`, and `postgres`.

### Common Docker Commands

```bash
# View all logs
docker compose logs -f

# Run migrations
docker compose exec web python manage.py migrate

# Create admin user
docker compose exec web python manage.py createsuperuser

# Seed data sources
docker compose exec web python manage.py seed_datasources

# Stop everything
docker compose down

# Or use the Makefile
make up        # docker compose up -d --build
make logs      # docker compose logs -f
make seed-docker
make bash-web
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | — | Django secret key (generate with `python -c 'import secrets; print(secrets.token_urlsafe(50))'`) |
| `DEBUG` | No | `True` | Django debug mode (set `False` in production) |
| `DATABASE_URL` | No | `sqlite:///db.sqlite3` | Database URL. Use `postgres://user:pass@host:5432/dbname` for PostgreSQL |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string for Celery broker |
| `DEEPSEEK_API_KEY` | No | — | DeepSeek API key for LLM-powered data collection |
| `DEEPSEEK_MODEL` | No | `deepseek-chat` | DeepSeek model name |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `CSRF_TRUSTED_ORIGINS` | No | `http://localhost:8000` | Comma-separated trusted origins |

### Data Collection

The app uses Celery Beat to schedule periodic data collection. Tasks are managed via `django-celery-beat` and can be configured in the Django admin at `/admin/django_celery_beat/`.

**Task schedule:**

| Task | Default Interval | Description |
|------|-----------------|-------------|
| `collect_all_sources` | Every 15 min | Dispatches all active DataSources to their respective collectors |
| `collect_news_articles` | Every 30 min | Fetches tech news from RSS feeds |
| `collect_llm_source` | Every 4 hours | DeepSeek searches for new layoff announcements |
| `enrich_pending_events` | Every hour | LLM enriches unverified events with industry/AI/confidence data |
| `cleanup_stale_data` | Daily at 3am | Removes scrape logs older than 30 days |

### LLM-Powered Collection

With a `DEEPSEEK_API_KEY` configured, the app can:

1. **Proactively find layoffs** — Queries DeepSeek every 4 hours for new layoff announcements
2. **Enrich events** — Fills in missing industry, AI-tag, and confidence scores
3. **Extract from articles** — Parses full article text to extract structured layoff data

The collector uses OpenAI-compatible API format, so it can also work with any OpenAI-compatible provider (OpenAI, Anthropic via proxy, local Ollama, etc.) by changing `DEEPSEEK_BASE_URL` in settings.

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/layoffs/` | GET | List layoff events (paginated) |
| `/api/layoffs/?verified=true` | GET | Filter by verified status |
| `/api/layoffs/?ai=true` | GET | Filter AI-related layoffs only |
| `/api/layoffs/?industry=SaaS` | GET | Filter by industry |
| `/api/layoffs/?days=7` | GET | Filter by recency |
| `/api/layoffs/?search=Meta` | GET | Search by company name |
| `/api/layoffs/?ordering=-headcount` | GET | Order by headcount (desc) |
| `/api/news/` | GET | List news articles |
| `/api/stats/` | GET | Aggregate statistics dashboard |

## Deployment (VPS + Cloudflare)

### 1. Server Setup

```bash
# Ubuntu 22.04+
sudo apt update && sudo apt install docker.io docker-compose-plugin -y
```

### 2. Deploy

```bash
git clone https://github.com/yourusername/layoffs.git /app
cd /app
cp .env.example .env
# Edit .env with production values:
#   DEBUG=False
#   SECRET_KEY=<generated-key>
#   DATABASE_URL=postgres://layoffs:password@db:5432/layoffs
#   REDIS_URL=redis://redis:6379/0
#   DEEPSEEK_API_KEY=<key>
#   ALLOWED_HOSTS=layoffs.icu,www.layoffs.icu
#   CSRF_TRUSTED_ORIGINS=https://layoffs.icu,https://www.layoffs.icu

docker compose up -d --build
```

### 3. First-Time Setup

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_datasources
```

### 4. Cloudflare DNS

Create A records pointing to your VPS IP:
- `layoffs.icu` → VPS IP (proxied)
- `www.layoffs.icu` → VPS IP (proxied)

Enable SSL/TLS: **Full (strict)** in Cloudflare dashboard.

### 5. Nginx (on host)

The Docker Compose stack exposes port 8000. For production, either:
- Run nginx on the host as a reverse proxy to `localhost:8000`
- Use a reverse proxy container

The included `nginx/default.conf` is configured for the Docker Compose network (upstream `web:8000`).

## Project Structure

```
layoffs/
├── docs/                           # Phase-by-phase documentation
├── layoffs_tracker/                # Django project config
│   ├── settings.py                 # All configuration
│   ├── celery.py                   # Celery app setup
│   └── urls.py                     # Root URL routing
├── layoffs/                        # Core app
│   ├── models.py                   # LayoffEvent model
│   ├── views.py                    # Template + DRF + HTMX views
│   ├── serializers.py              # DRF serializers
│   ├── admin.py                    # Admin configuration
│   ├── templates/                  # HTML templates
│   └── static/                     # CSS, JS assets
├── news/                           # Tech news app
│   ├── models.py                   # NewsArticle model
│   └── admin.py
├── scraper/                        # Data collection app
│   ├── models.py                   # DataSource, ScrapedArticle, ScrapeLog
│   ├── tasks.py                    # Celery periodic tasks
│   ├── pipeline.py                 # Dedup & merge pipeline
│   └── collectors/                 # RSS, Web, LLM collectors
├── community/                      # Forum app (models ready)
├── nginx/                          # Nginx config
├── Dockerfile                      # Multi-stage build
├── docker-compose.yml              # Full stack orchestration
├── Makefile                        # Dev & Docker shortcuts
└── .env.example                    # Environment template
```

## Makefile Commands

```bash
make dev              # Run Django dev server
make migrate          # Run makemigrations + migrate
make check            # Django system checks
make shell            # Django shell
make superuser        # Create admin user
make seed             # Seed data sources
make test             # Run tests
make up               # docker compose up -d --build
make down             # docker compose down
make logs             # Tail all docker logs
make logs-web         # Tail web container logs
make bash-web         # Open shell in web container
make migrate-docker   # Run migrations in Docker
make seed-docker      # Seed data sources in Docker
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run checks: `python manage.py check`
5. Commit with descriptive messages: `git commit -m "add: brief description of changes"`
6. Push: `git push origin feat/my-feature`
7. Open a pull request

### Code Style

- Python: Follow PEP 8, use descriptive names, keep functions focused
- Django: Use class-based views, model forms, and DRF serializers
- Templates: Use partials for HTMX components, avoid inline scripts
- CSS: Use the existing CSS custom properties (theme variables)

## License

MIT
