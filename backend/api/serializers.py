from rest_framework import serializers
from .models import Post, Report
from .helpers.time_formatter import format_timeago
from django.utils import timezone

class PostSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    class Meta:
        model = Post
        fields = '__all__'
        read_only_fields = ['user_id']
    def get_created_at(self, obj):
        delta = timezone.now() - obj.created_at
        return format_timeago(delta)
        

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = ['user_id']