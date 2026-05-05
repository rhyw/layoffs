# TODO

> Generated from implementation assessment against original requirements.

## High Priority

- [ ] **Web scraper** — `collect_web_source()` fetches HTML but never parses it. Build `scraper/collectors/web_scraper.py` to extract layoff data from known sources using the heuristic pipeline.
- [ ] **Community CRUD** — No `community/urls.py`, no views, no thread/reply forms. Sidebar stats are hardcoded zeros.
- [ ] **Layoff detail page** — No `/layoffs/{id}/` route to view a single event's full details.
- [ ] **User auth UI** — No login/signup in header. User FK exists on models but no way to register.

## Medium Priority

- [ ] **Dashboard view context** — `DashboardView.get_context_data()` is empty. Charts work via client-side JS but server context is missing.
- [ ] **Rate limiting / politeness** — No delays, no rotating User-Agents across collectors.
- [ ] **Beat schedule tuning** — Currently twice daily. Adjust intervals as needed.

## Low Priority

- [ ] **404 error page** — No `templates/404.html`.
- [ ] **Tests** — All 4 `tests.py` files are stubs. Zero test coverage.

## Done

- [x] Project scaffolding (Django, apps, config)
- [x] Data models (all 7 models + admin)
- [x] Celery infrastructure (broker, beat, tasks)
- [x] RSS feed collector (feefparser + keyword filtering)
- [x] LLM-powered collector (DeepSeek: query + extraction + enrichment)
- [x] News article collector (The Verge, TechCrunch, Ars, Wired)
- [x] Dedup & merge pipeline (normalize, dedup, heuristic extraction)
- [x] Seed datasources management command
- [x] DRF API (layoffs, news, stats endpoints with filtering)
- [x] HTMX partials (recent disclosures with sort/pagination, tech news, stats)
- [x] Homepage with grid layout, community sidebar, news section
- [x] Dashboard with Chart.js charts
- [x] Dark/light theme toggle
- [x] Docker Compose (5 services: web, worker, beat, redis, postgres)
- [x] Multi-stage Docker build with auto-migration/seeding
- [x] Nginx reverse proxy config
- [x] Sample data fixture
- [x] Pagination (10 per page, HTMX-powered)
- [x] Sortable columns (all 5 columns via HTMX)
- [x] Local HTMX serving (no CDN dependency)
- [x] Removed layoffs.icu from collector code
