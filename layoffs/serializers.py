from rest_framework import serializers
from .models import LayoffEvent


class LayoffEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayoffEvent
        fields = '__all__'


class LayoffStatsSerializer(serializers.Serializer):
    total_companies = serializers.IntegerField()
    total_laid_off = serializers.IntegerField()
    avg_percentage = serializers.FloatField()
    most_recent_date = serializers.DateField()
    by_industry = serializers.ListField()
    by_month = serializers.ListField()
