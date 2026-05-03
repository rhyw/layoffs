from rest_framework import viewsets
from .models import NewsArticle
from .serializers import NewsArticleSerializer


class NewsArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NewsArticle.objects.all()
    serializer_class = NewsArticleSerializer
    filterset_fields = ['source', 'topic_tag']
    ordering = ['-published_at']
