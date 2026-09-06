from django.contrib import admin

from .models import Badge, MissionProgress, SeasonalMission, UserBadge


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'awarded_at')
    list_filter = ('badge',)


@admin.register(SeasonalMission)
class SeasonalMissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'category', 'required_count', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'region', 'category')


@admin.register(MissionProgress)
class MissionProgressAdmin(admin.ModelAdmin):
    list_display = ('mission', 'user', 'progress_count', 'completed_at')
    list_filter = ('mission',)
