from django.contrib import admin
from .models import Thread, Reply


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'created_by', 'reply_count',
                    'is_pinned', 'created_at')
    list_filter = ('category', 'is_pinned', 'created_at')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('thread', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content',)
