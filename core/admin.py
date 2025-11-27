from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'escola')
    list_filter = ('escola',)
    search_fields = ('user__username', 'escola__nome')