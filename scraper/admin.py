from django.contrib import admin
from .models import DataSource, ScrapedArticle, ScrapeLog


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'is_active', 'interval_minutes',
                    'last_fetched', 'consecutive_failures')
    list_filter = ('source_type', 'is_active')
    search_fields = ('name', 'url')


@admin.register(ScrapedArticle)
class ScrapedArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'fetched_at', 'processed')
    list_filter = ('processed', 'source', 'fetched_at')
    search_fields = ('title',)


@admin.register(ScrapeLog)
class ScrapeLogAdmin(admin.ModelAdmin):
    list_display = ('source', 'status', 'articles_found',
                    'articles_created', 'ran_at', 'duration_seconds')
    list_filter = ('status', 'source', 'ran_at')
