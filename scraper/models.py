from django.db import models


class DataSource(models.Model):
    SOURCE_TYPES = [
        ('rss', 'RSS Feed'),
        ('api', 'API Endpoint'),
        ('web', 'Web Scrape'),
        ('llm', 'LLM Query'),
    ]

    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    url = models.URLField(max_length=1024)
    interval_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)
    last_fetched = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Data Source'
        verbose_name_plural = 'Data Sources'

    def __str__(self):
        return f'{self.name} ({self.get_source_type_display()})'


class ScrapedArticle(models.Model):
    url = models.URLField(max_length=1024, blank=True, default='')
    url_hash = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.TextField()
    content_hash = models.CharField(max_length=64, db_index=True)
    source = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name='scraped_articles'
    )
    fetched_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    matched_event = models.ForeignKey(
        'layoffs.LayoffEvent', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='scraped_articles'
    )

    class Meta:
        ordering = ['-fetched_at']
        verbose_name = 'Scraped Article'
        verbose_name_plural = 'Scraped Articles'

    def __str__(self):
        return self.title[:80]


class ScrapeLog(models.Model):
    source = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name='logs'
    )
    status = models.CharField(
        max_length=20,
        choices=[('success', 'Success'), ('failed', 'Failed')]
    )
    message = models.TextField(blank=True, default='')
    articles_found = models.PositiveIntegerField(default=0)
    articles_created = models.PositiveIntegerField(default=0)
    ran_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.FloatField(default=0.0)

    class Meta:
        ordering = ['-ran_at']
        verbose_name = 'Scrape Log'
        verbose_name_plural = 'Scrape Logs'

    def __str__(self):
        return f'{self.source.name} - {self.status} @ {self.ran_at}'
