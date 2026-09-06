from django.contrib import admin
from django.utils import timezone

from .models import Report
from .tasks import send_report_processed_email


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'content_type', 'object_id', 'reporter', 'status', 'created_at')
    list_filter = ('status', 'content_type')
    readonly_fields = ('reporter', 'content_type', 'object_id', 'reason', 'created_at')
    actions = ['mark_resolved', 'mark_rejected']

    def _resolve(self, request, queryset, status):
        report_ids = list(queryset.values_list('id', flat=True))
        queryset.update(status=status, resolved_by=request.user, resolved_at=timezone.now())
        for report_id in report_ids:
            send_report_processed_email.delay(report_id)

    @admin.action(description='Đánh dấu đã xử lý')
    def mark_resolved(self, request, queryset):
        self._resolve(request, queryset, Report.Status.RESOLVED)

    @admin.action(description='Đánh dấu từ chối (không vi phạm)')
    def mark_rejected(self, request, queryset):
        self._resolve(request, queryset, Report.Status.REJECTED)
