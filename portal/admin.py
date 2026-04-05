from django.contrib import admin
from .models import Circular, UserActivity

@admin.register(Circular)
class CircularAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'status', 'author', 'published_at', 'created_at']
    list_filter = ['status', 'priority']
    search_fields = ['title', 'body']
    readonly_fields = ['created_at', 'updated_at']

admin.site.register(UserActivity)
