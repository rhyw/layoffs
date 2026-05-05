"""
Management command to seed initial DataSource records into the database.

Usage:
    python manage.py seed_datasources
"""
from django.core.management.base import BaseCommand
from scraper.models import DataSource


INITIAL_SOURCES = [
    {
        'name': 'Google News (Layoffs)',
        'source_type': 'rss',
        'url': 'https://news.google.com/rss/search?q=layoffs&hl=en-US&gl=US&ceid=US:en',
        'interval_minutes': 15,
    },
    {
        'name': 'TechCrunch',
        'source_type': 'rss',
        'url': 'https://techcrunch.com/feed/',
        'interval_minutes': 15,
    },
    {
        'name': 'Reuters Technology',
        'source_type': 'rss',
        'url': 'https://www.reutersagency.com/feed/?best-topics=tech',
        'interval_minutes': 15,
    },
    {
        'name': 'DeepSeek Research',
        'source_type': 'llm',
        'url': 'https://api.deepseek.com/v1',
        'interval_minutes': 240,
    },
    {
        'name': 'The Verge',
        'source_type': 'web',
        'url': 'https://www.theverge.com/tech',
        'interval_minutes': 30,
    },
]


class Command(BaseCommand):
    help = 'Seed initial DataSource records for layoff data collection'

    def handle(self, *args, **options):
        created = 0
        existing = 0

        for source_data in INITIAL_SOURCES:
            _, was_created = DataSource.objects.get_or_create(
                name=source_data['name'],
                defaults=source_data,
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {source_data["name"]}'))
            else:
                existing += 1
                self.stdout.write(f'Already exists: {source_data["name"]}')

        self.stdout.write(
            self.style.SUCCESS(f'Done. {created} created, {existing} already existing.')
        )
