from django.contrib import admin
from .models import LayoffEvent


@admin.register(LayoffEvent)
class LayoffEventAdmin(admin.ModelAdmin):
    list_display = ('company', 'headcount', 'percentage', 'date_reported',
                    'source_name', 'is_ai_related', 'is_verified')
    list_filter = ('is_ai_related', 'is_verified', 'industry', 'date_reported')
    search_fields = ('company', 'notes', 'source_name')
    date_hierarchy = 'date_reported'
    ordering = ('-date_reported',)
    list_editable = ('is_verified', 'is_ai_related')
