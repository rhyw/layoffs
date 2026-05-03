# Phase 1: Project Scaffolding

## Goal
Set up the Django project structure with all necessary apps, dependencies, and configuration.

## Steps

### 1.1 Create Django Project
- Use `django-admin startproject layoffs_tracker` or `uv`-based approach
- Project root: `/app/layoffs_tracker/`

### 1.2 Create Django Apps
| App | Purpose |
|-----|---------|
| `layoffs` | Core layoff event data model, views, templates |
| `news` | Tech news articles model and views |
| `community` | Discussion threads (forum feature) |
| `scraper` | Celery tasks, data source config, management commands |

### 1.3 Dependencies (`requirements.txt` or `pyproject.toml`)
```
Django>=5.0
djangorestframework
celery[redis]
django-celery-beat
django-htmx
beautifulsoup4
requests
feedparser
newspaper3k
openai
pydantic
django-environ
psycopg2-binary
gunicorn
whitenoise
```

### 1.4 Configuration (`settings.py`)
- Environment-based config via `django-environ`
- Database: PostgreSQL (read from DATABASE_URL env var)
- Celery: Redis as broker (read from REDIS_URL env var)
- Static files: WhiteNoise for production
- Installed apps include all 4 custom apps + third-party
- HTMX middleware enabled
- Dark mode by default with localStorage persistence

### 1.5 Environment File (`.env`)
```
SECRET_KEY=...
DEBUG=True
DATABASE_URL=postgres://layoffs:password@localhost:5432/layoffs
REDIS_URL=redis://localhost:6379/0
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-chat
```

### 1.6 Project Structure
```
/Users/yuwang/code/layoffs/
├── docs/
├── .env
├── pyproject.toml
├── manage.py
├── layoffs_tracker/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── layoffs/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── templates/
│   └── admin.py
├── news/
│   ├── models.py
│   ├── views.py
│   └── admin.py
├── scraper/
│   ├── models.py
│   ├── tasks.py
│   └── collectors/
└── community/
    ├── models.py
    ├── views.py
    └── urls.py
```

## Deliverables
- Working Django project that starts with `python manage.py runserver`
- All 4 apps registered and importable
- Celery app configured and importable
- Database migrations created for any initial models
