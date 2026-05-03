from django.db import models


class NewsArticle(models.Model):
    title = models.CharField(max_length=512)
    snippet = models.TextField(blank=True, default='')
    source = models.CharField(max_length=255)
    source_url = models.URLField(max_length=1024, unique=True)
    thumbnail_url = models.URLField(max_length=1024, null=True, blank=True)
    topic_tag = models.CharField(max_length=100, null=True, blank=True)
    published_at = models.DateTimeField(db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'News Article'
        verbose_name_plural = 'News Articles'

    def __str__(self):
        return self.title
