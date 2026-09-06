from django.contrib import admin

from .models import CheckIn, Comment, Review, ReviewTag


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('place', 'user', 'rating', 'is_hidden', 'created_at')
    list_filter = ('rating', 'is_hidden')
    search_fields = ('place__name', 'user__username')
    actions = ['hide_reviews', 'restore_reviews']

    @admin.action(description='Ẩn đánh giá vi phạm')
    def hide_reviews(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description='Khôi phục đánh giá')
    def restore_reviews(self, request, queryset):
        queryset.update(is_hidden=False)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'created_at')


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ('user', 'place', 'distance_m', 'is_valid', 'created_at')
    list_filter = ('is_valid',)


@admin.register(ReviewTag)
class ReviewTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
