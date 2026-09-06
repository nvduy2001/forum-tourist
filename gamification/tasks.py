from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count
from django.utils import timezone

from .models import Badge, SeasonalMission, UserBadge


@shared_task
def close_expired_seasonal_missions():
    """Celery beat task: tự đóng các seasonal mission đã hết hạn (end_date < hôm nay)."""
    today = timezone.localdate()
    return SeasonalMission.objects.filter(is_active=True, end_date__lt=today).update(is_active=False)


@shared_task
def send_badge_awarded_email(user_badge_id):
    """Gửi thông báo qua email khi user được cấp huy hiệu (bao gồm 'Người khai phá' và huy hiệu mission)."""
    try:
        user_badge = UserBadge.objects.select_related('user', 'badge').get(pk=user_badge_id)
    except UserBadge.DoesNotExist:
        return

    user = user_badge.user
    if not user.email:
        return

    send_mail(
        subject=f'Bạn vừa nhận huy hiệu "{user_badge.badge.name}"',
        message=(
            f'Chào {user.username},\n\n'
            f'Bạn vừa được trao huy hiệu "{user_badge.badge.name}" trên Forum Tourist.\n'
            f'{user_badge.badge.description}\n'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def _previous_month_range(today):
    first_of_this_month = today.replace(day=1)
    last_day_prev_month = first_of_this_month - timezone.timedelta(days=1)
    start = last_day_prev_month.replace(day=1)
    end = last_day_prev_month
    return start, end


@shared_task
def award_monthly_badges():
    """Celery beat (chạy đầu tháng): cấp huy hiệu 'Người đánh giá tháng' cho user viết nhiều review nhất
    tháng trước, và 'Chuyên gia ẩm thực' cho user viết nhiều review category='food' nhất tháng trước."""
    from reviews.models import Review

    today = timezone.localdate()
    start, end = _previous_month_range(today)
    month_label = start.strftime('%m-%Y')

    _award_top_reviewer(
        Review.objects.filter(created_at__date__range=(start, end)),
        name=f'Người đánh giá tháng {month_label}',
        slug=f'nguoi-danh-gia-thang-{start.strftime("%Y-%m")}',
        description='Viết nhiều đánh giá nhất trong tháng.',
    )
    _award_top_reviewer(
        Review.objects.filter(created_at__date__range=(start, end), place__category='food'),
        name=f'Chuyên gia ẩm thực tháng {month_label}',
        slug=f'chuyen-gia-am-thuc-{start.strftime("%Y-%m")}',
        description='Viết nhiều đánh giá ẩm thực nhất trong tháng.',
    )


def _award_top_reviewer(queryset, name, slug, description):
    top = (
        queryset.values('user')
        .annotate(review_count=Count('id'))
        .order_by('-review_count')
        .first()
    )
    if not top or top['review_count'] == 0:
        return

    badge, _ = Badge.objects.get_or_create(slug=slug, defaults={'name': name, 'description': description})
    UserBadge.objects.get_or_create(user_id=top['user'], badge=badge)
