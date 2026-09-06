from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from moderation.tasks import send_user_warning_email

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ('is_business_owner', 'is_active', 'points')
    fieldsets = UserAdmin.fieldsets + (
        ('Business owner', {'fields': ('is_business_owner', 'owned_place')}),
        ('Hồ sơ & điểm thưởng', {'fields': ('avatar', 'cover_image', 'bio', 'points')}),
    )
    actions = ['send_warning']

    @admin.action(description='Gửi cảnh báo vi phạm quy định qua email')
    def send_warning(self, request, queryset):
        message = (
            'Tài khoản của bạn vừa nhận một cảnh báo từ quản trị viên do vi phạm quy định cộng đồng. '
            'Vi phạm lặp lại có thể dẫn đến khóa tài khoản.'
        )
        for user in queryset:
            send_user_warning_email.delay(user.id, message)
