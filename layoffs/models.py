from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class LayoffEvent(models.Model):
    company = models.CharField(max_length=255, db_index=True)
    headcount = models.PositiveIntegerField(null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    date_reported = models.DateField(db_index=True)
    date_published = models.DateTimeField(auto_now_add=True)
    source_url = models.URLField(max_length=1024)
    source_name = models.CharField(max_length=255, blank=True, default='')
    is_ai_related = models.BooleanField(default=False, db_index=True)
    industry = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    confidence_score = models.FloatField(default=0.0)
    is_verified = models.BooleanField(default=False, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'date_reported', 'headcount'],
                name='unique_layoff_event',
            )
        ]
        ordering = ['-date_reported']
        verbose_name = 'Layoff Event'
        verbose_name_plural = 'Layoff Events'
        indexes = [
            models.Index(fields=['-date_reported', 'is_verified']),
        ]

    def _generate_slug(self):
        base = slugify(self.company)[:200] or 'unknown'
        base = f'{base}-{self.date_reported}'
        if self.headcount:
            base = f'{base}-{self.headcount}'
        return base

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_slug()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('layoff-detail', kwargs={'slug': self.slug})

    def __str__(self):
        count = f'{self.headcount:,}' if self.headcount else '?'
        return f'{self.company} - {count} jobs ({self.date_reported})'
