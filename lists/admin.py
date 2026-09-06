from django.contrib import admin

from .models import List, ListItem


class ListItemInline(admin.TabularInline):
    model = ListItem
    extra = 0


@admin.register(List)
class ListAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_public', 'created_at')
    list_filter = ('is_public',)
    search_fields = ('name', 'user__username')
    inlines = [ListItemInline]
