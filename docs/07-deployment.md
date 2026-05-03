# Phase 7: Deployment (VPS + Cloudflare)

## Goal
Deploy the application on a VPS with Docker Compose, with Cloudflare for DNS and reverse proxy.

## Architecture

```
Internet ──► Cloudflare (DNS + Proxy) ──► VPS :80/:443
                                                │
                                          Nginx (reverse proxy)
                                           /          \
                                    Gunicorn        Static Files
                                        │              (Whitenoise)
                                   Django App
                                        │
                                   Celery Worker ←── Redis
                                        │
                                   PostgreSQL
```

## Infrastructure

### 7.1 Docker Compose (`docker-compose.yml`)

```yaml
services:
  web:
    build: .
    command: gunicorn layoffs_tracker.wsgi:application --bind 0.0.0.0:8000
    env_file: .env
    depends_on: [db, redis]
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media

  worker:
    build: .
    command: celery -A layoffs_tracker worker -l info
    env_file: .env
    depends_on: [db, redis]

  beat:
    build: .
    command: celery -A layoffs_tracker beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file: .env
    depends_on: [db, redis]

  redis:
    image: redis:7-alpine

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file: .env

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### 7.2 Nginx Config (on host or in container)

```nginx
server {
    listen 80;
    server_name layoffs.icu www.layoffs.icu;

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
    }

    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 7.3 Cloudflare Setup
1. Point DNS records to VPS IP:
   - `A` record for `layoffs.icu` → VPS IP (proxied through Cloudflare)
   - `A` record for `www.layoffs.icu` → VPS IP (proxied)
2. Enable SSL/TLS: Full (strict)
3. Configure Page Rules or use Cloudflare Tunnel for additional security

### 7.4 VPS Setup Steps
```bash
# 1. Install Docker & Docker Compose on Ubuntu 22.04
sudo apt update && sudo apt install docker.io docker-compose-plugin

# 2. Clone repo
git clone https://github.com/yourusername/layoffs.git /app

# 3. Create .env file
cp .env.example .env
# Edit .env with production values, generate SECRET_KEY

# 4. Build & start
docker compose up -d --build

# 5. Run migrations
docker compose exec web python manage.py migrate

# 6. Collect static files
docker compose exec web python manage.py collectstatic --noinput

# 7. Create superuser
docker compose exec web python manage.py createsuperuser

# 8. Install and configure nginx on host
# (or use a reverse proxy container)
```

### 7.5 Environment Variables (Production)
```
SECRET_KEY=<generated-random-key>
DEBUG=False
DATABASE_URL=postgres://layoffs:<password>@db:5432/layoffs
REDIS_URL=redis://redis:6379/0
DEEPSEEK_API_KEY=<key>
DEEPSEEK_MODEL=deepseek-chat
ALLOWED_HOSTS=layoffs.icu,www.layoffs.icu
CSRF_TRUSTED_ORIGINS=https://layoffs.icu,https://www.layoffs.icu
```

### 7.6 Database Backup Strategy
- Daily PostgreSQL dump via cron inside container
- Backups stored on host at `/var/backups/layoffs/`
- Retention: 30 days
- Optional: upload to S3-compatible storage

### 7.7 Monitoring
- `docker compose logs --tail=50 web` for app logs
- `celery -A layoffs_tracker inspect active` for task queue status
- Uptime monitoring via Cloudflare

### 7.8 SSL/TLS
- Handled by Cloudflare (Flexible or Full Strict)
- No need for certbot on the VPS
- If using direct HTTPS: certbot + Let's Encrypt
