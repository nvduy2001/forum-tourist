from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import PlaceOwnershipRequest


@shared_task
def send_ownership_request_result_email(request_id):
    """Thông báo cho user kết quả duyệt/từ chối yêu cầu xác minh chủ địa điểm."""
    try:
        req = PlaceOwnershipRequest.objects.select_related('user', 'place').get(pk=request_id)
    except PlaceOwnershipRequest.DoesNotExist:
        return

    if not req.user.email:
        return

    if req.status == PlaceOwnershipRequest.Status.APPROVED:
        subject = f'Yêu cầu xác minh chủ địa điểm "{req.place.name}" đã được duyệt'
        message = (
            f'Chào {req.user.username},\n\n'
            f'Bạn đã được xác nhận là chủ sở hữu của "{req.place.name}" trên Forum Tourist.\n'
        )
    else:
        subject = f'Yêu cầu xác minh chủ địa điểm "{req.place.name}" chưa được duyệt'
        message = (
            f'Chào {req.user.username},\n\n'
            f'Yêu cầu xác minh chủ sở hữu địa điểm "{req.place.name}" của bạn chưa được duyệt. '
            f'Vui lòng kiểm tra lại thông tin liên hệ và gửi lại nếu cần.\n'
        )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[req.user.email],
        fail_silently=True,
    )
