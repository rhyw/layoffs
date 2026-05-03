from django.db import models
from django.conf import settings


class Thread(models.Model):
    CATEGORIES = [
        ('general', 'General Discussions'),
        ('networking', 'Networking & Referrals'),
        ('interviews', 'Interviews'),
        ('career', 'Career Advice'),
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=50, choices=CATEGORIES, default='general')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='threads'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reply_count = models.PositiveIntegerField(default=0)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_pinned', '-updated_at']
        verbose_name = 'Thread'
        verbose_name_plural = 'Threads'

    def __str__(self):
        return self.title


class Reply(models.Model):
    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, related_name='replies'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='replies'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Reply'
        verbose_name_plural = 'Replies'

    def __str__(self):
        return f'Reply by {self.author} on {self.thread.title[:50]}'
