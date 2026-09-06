from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Report


@shared_task
def send_report_processed_email(report_id):
    """Thông báo cho người báo cáo khi Report của họ đã được Admin xử lý."""
    try:
        report = Report.objects.select_related('reporter').get(pk=report_id)
    except Report.DoesNotExist:
        return

    if not report.reporter.email:
        return

    status_label = 'đã xử lý (vi phạm)' if report.status == Report.Status.RESOLVED else 'không vi phạm'
    send_mail(
        subject='Báo cáo của bạn đã được xử lý',
        message=(
            f'Chào {report.reporter.username},\n\n'
            f'Báo cáo #{report.pk} của bạn đã được Admin xem xét và đánh dấu là: {status_label}.\n'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[report.reporter.email],
        fail_silently=True,
    )


@shared_task
def send_user_warning_email(user_id, message):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    if not user.email:
        return

    send_mail(
        subject='Cảnh báo từ quản trị viên Forum Tourist',
        message=f'Chào {user.username},\n\n{message}\n',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
