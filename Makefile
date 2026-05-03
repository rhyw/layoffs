.PHONY: dev migrate check shell superuser collectstatic seed test

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
