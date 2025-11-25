from django.contrib import admin
from .models import MetabaseOAuthToken


@admin.register(MetabaseOAuthToken)
class MetabaseOAuthTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'mb_username', 'created_at', 'updated_at')
    search_fields = ('user__username', 'mb_username')
