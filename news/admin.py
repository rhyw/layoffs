from django.contrib import admin
from .models import NewsArticle


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'published_at', 'topic_tag')
    list_filter = ('source', 'topic_tag', 'published_at')
    search_fields = ('title', 'snippet')
    date_hierarchy = 'published_at'
    ordering = ('-published_at',)
