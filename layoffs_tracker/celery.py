import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'layoffs_tracker.settings')

app = Celery('layoffs_tracker')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
