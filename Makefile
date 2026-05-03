.PHONY: dev migrate check shell superuser collectstatic seed test trigger trigger-docker

# ── Local Development ──

dev:
	python manage.py runserver

migrate:
	python manage.py makemigrations
	python manage.py migrate

check:
	python manage.py check

shell:
	python manage.py shell_plus --ipython

superuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput

seed:
	python manage.py seed_datasources

test:
	python manage.py test

# ── Docker ──

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

logs-web:
	docker compose logs -f web

logs-worker:
	docker compose logs -f worker

bash-web:
	docker compose exec web bash

migrate-docker:
	docker compose exec web python manage.py migrate

superuser-docker:
	docker compose exec web python manage.py createsuperuser

seed-docker:
	docker compose exec web python manage.py seed_datasources

# ── Task Triggering ──

# Dispatches all Celery Beat tasks immediately (useful for testing — avoids waiting for cron)
trigger:
	python manage.py shell -c "from django.conf import settings as s; from importlib import import_module as im; [print(f'  {n}: dispatched ({getattr(im(p),t).delay().id})') for n,c in s.CELERY_BEAT_SCHEDULE.items() for p,_,t in [c['task'].rpartition('.')]]"

trigger-docker:
	docker compose exec web python manage.py shell -c "from django.conf import settings as s; from importlib import import_module as im; [print(f'  {n}: dispatched ({getattr(im(p),t).delay().id})') for n,c in s.CELERY_BEAT_SCHEDULE.items() for p,_,t in [c['task'].rpartition('.')]]"
