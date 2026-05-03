# Phase 2: Data Models

## Goal
Define all database models for layoff events, news articles, data sources, and community features.

## Models

### 2.1 LayoffEvent (`layoffs/models.py`)

```python
class LayoffEvent(models.Model):
    company = models.CharField(max_length=255, db_index=True)
    headcount = models.PositiveIntegerField(null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    date_reported = models.DateField(db_index=True)
    date_published = models.DateTimeField(auto_now_add=True)
    source_url = models.URLField(max_length=1024)
    source_name = models.CharField(max_length=255)
    is_ai_related = models.BooleanField(default=False, db_index=True)
    industry = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    confidence_score = models.FloatField(default=0.0)
    is_verified = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ('company', 'date_reported', 'headcount')
        ordering = ['-date_reported']
        verbose_name = "Layoff Event"
        verbose_name_plural = "Layoff Events"

    def __str__(self):
        return f"{self.company} - {self.headcount or '?'} jobs ({self.date_reported})"
```

### 2.2 NewsArticle (`news/models.py`)

```python
class NewsArticle(models.Model):
    title = models.CharField(max_length=512)
    snippet = models.TextField()
    source = models.CharField(max_length=255)
    source_url = models.URLField(max_length=1024, unique=True)
    thumbnail_url = models.URLField(max_length=1024, null=True, blank=True)
    topic_tag = models.CharField(max_length=100, null=True, blank=True)
    published_at = models.DateTimeField(db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at']
        verbose_name = "News Article"
        verbose_name_plural = "News Articles"

    def __str__(self):
        return self.title
```

### 2.3 DataSource (`scraper/models.py`)

```python
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Data Source"
        verbose_name_plural = "Data Sources"

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"
```

### 2.4 ScrapedArticle (log of what was ingested, for dedup)

```python
class ScrapedArticle(models.Model):
    url_hash = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.TextField()
    content_hash = models.CharField(max_length=64, db_index=True)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    fetched_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    matched_event = models.ForeignKey(LayoffEvent, null=True, blank=True, on_delete=models.SET_NULL)
```

### 2.5 Community Models (`community/models.py`)

```python
class Thread(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=100, choices=[...])
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    reply_count = models.PositiveIntegerField(default=0)

class Reply(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

## Admin Registrations
All models registered in their respective `admin.py` with:
- List display, search fields, list filters
- Date hierarchy for time-based browsing
- Inline editing where appropriate

## Migrations
- `python manage.py makemigrations layoffs news scraper community`
- `python manage.py migrate`
