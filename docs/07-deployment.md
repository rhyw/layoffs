# Deployment Guide

Two deployment targets:

- **VPS** — runs the full Django app (web + API + Celery + PostgreSQL)
- **GitHub Pages** — hosts a static demo page that reads from the VPS API

---

## Prerequisites

- A VPS (Ubuntu 22.04+) with a public IP
- A domain managed in Cloudflare (e.g. `yourdomain.com`)
- GitHub repository with your code pushed

Throughout this guide, replace:

| Placeholder | Replace with |
|---|---|
| `yourdomain.com` | Your actual domain |
| `myname` | Your GitHub username |
| `<your-vps-ip>` | Your VPS public IP |
| `<generate-a-random-key>` | Output of `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `<choose-a-password>` | A strong PostgreSQL password |

Also update the following files with your real values before starting:

- `nginx/default.conf` — `server_name layoffs.yourdomain.com;`
- `layoffs_tracker/settings.py:164` — `'https://myname.github.io'` → `'https://<your-username>.github.io'`
- `demo/index.html:86` — the footer link to your domain

---

## 1. Architecture

```
                            Cloudflare
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
  myname.github.io        layoffs.yourdomain.com    │
  (GitHub Pages)          (VPS Docker)              │
       │                        │                   │
       │  JS fetch(/api/*)      │                   │
       └────── CORS ────────────┘                   │
                                                    │
  Browser ────────── HTTPS ─────────────────────────┘
```

- `myname.github.io/layoffs-tracker/` — public demo (static HTML, client-side JS)
- `layoffs.yourdomain.com` — Django backend (hidden from public links)
- Cloudflare proxies `layoffs.yourdomain.com` for SSL + DDoS protection

---

## 2. VPS Setup

### 2.1 Initial VPS Configuration

```bash
ssh root@<your-vps-ip>

apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt install -y docker-compose-plugin

# Install nginx (as host reverse proxy)
apt install -y nginx
```

### 2.2 Clone Your Repository

```bash
git clone https://github.com/myname/layoffs-tracker.git /opt/layoffs-tracker
cd /opt/layoffs-tracker
```

### 2.3 Create `.env` File

```bash
cat > .env << 'ENVEOF'
DJANGO_SECRET_KEY=<generate-a-random-key>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=layoffs.yourdomain.com,localhost
DATABASE_URL=postgres://layoffs:<choose-a-password>@postgres:5432/layoffs
DATABASE_PASSWORD=<choose-a-password>
REDIS_URL=redis://redis:6379/0
DEEPSEEK_API_KEY=
CORS_ALLOWED_ORIGINS=https://myname.github.io
ENVEOF
```

### 2.4 Build and Start Docker Services

```bash
docker compose up -d --build
```

Verify everything is running:

```bash
docker compose ps
docker compose logs web --tail=20
```

### 2.5 Create a Superuser (for Django Admin)

```bash
docker compose exec web python manage.py createsuperuser
```

### 2.6 Configure Host Nginx

The Docker `web` container listens on port `8000`. Nginx on the host acts as a reverse proxy.

Create `/etc/nginx/sites-available/layoffs`:

```nginx
server {
    listen 80;
    server_name layoffs.yourdomain.com;
    client_max_body_size 10M;

    location /static/ {
        proxy_pass http://127.0.0.1:8000/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:

```bash
ln -sf /etc/nginx/sites-available/layoffs /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

---

## 3. Cloudflare DNS

In Cloudflare dashboard, add an A record:

| Type | Name | Content | Proxy status |
|---|---|---|---|
| A | `layoffs` | `<your-vps-ip>` | Proxied (orange cloud) |

Then set **SSL/TLS → Overview → Flexible**. This encrypts traffic between browsers and Cloudflare; Cloudflare reaches your VPS over plain HTTP (fine since the VPS is not the public face).

---

## 4. GitHub Pages

### 4.1 Configure Pages

In your GitHub repository:

1. **Settings → Pages → Source → GitHub Actions**
2. The workflow at `.github/workflows/deploy-pages.yml` handles deployment automatically
3. After pushing to `main`, the demo will be available at:
   `https://myname.github.io/layoffs-tracker/`

### 4.2 How It Works

The `demo/index.html` page:

1. Fetches stats from `https://layoffs.yourdomain.com/api/stats/`
2. Fetches layoff data from `https://layoffs.yourdomain.com/api/layoffs/`
3. Renders them in a table with stats summary
4. All API calls are CORS-allowed (configured in `settings.py`)

---

## 5. Automated Deploys (CI/CD)

Two GitHub Actions workflows run on every push to `main`:

| Workflow | File | What it does |
|---|---|---|
| Deploy demo to Pages | `.github/workflows/deploy-pages.yml` | Copies `demo/` → GitHub Pages |
| Deploy to VPS | `.github/workflows/deploy-vps.yml` | SSH into VPS, `git pull`, `docker compose up -d --build` |

### 5.1 Configure VPS Deploy Secrets

In GitHub repo → **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `VPS_HOST` | Your VPS IP address |
| `VPS_USER` | `root` (or your SSH user) |
| `VPS_SSH_KEY` | Your private SSH key (contents, not path) |

---

## 6. Version Summary

### Files you must edit before deploying

| File | What to change |
|---|---|
| `nginx/default.conf:7` | `server_name layoffs.yourdomain.com;` |
| `layoffs_tracker/settings.py:164` | `'https://myname.github.io'` → `'https://<your-username>.github.io'` |
| `demo/index.html:86` | `layoffs.mydomain.com` → `layoffs.yourdomain.com` |
| `demo/index.html:39,96` | `layoffs.mydomain.com` → `layoffs.yourdomain.com` |

### Result URLs

| URL | What | Who can access |
|---|---|---|
| `myname.github.io/layoffs-tracker/` | Public demo page | Anyone |
| `layoffs.yourdomain.com` | Full Django app | Direct access only |
| `layoffs.yourdomain.com/admin/` | Django admin | Direct access only |
