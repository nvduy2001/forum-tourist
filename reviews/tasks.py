from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Comment


@shared_task
def send_new_comment_email(comment_id):
    """Thông báo cho tác giả review khi có bình luận mới (trừ khi tự bình luận vào review của mình)."""
    try:
        comment = Comment.objects.select_related('user', 'review__user', 'review__place').get(pk=comment_id)
    except Comment.DoesNotExist:
        return

    review_author = comment.review.user
    if comment.user_id == review_author.id or not review_author.email:
        return

    send_mail(
        subject=f'{comment.user.username} đã bình luận về đánh giá của bạn',
        message=(
            f'Chào {review_author.username},\n\n'
            f'{comment.user.username} vừa bình luận về đánh giá của bạn cho "{comment.review.place.name}":\n'
            f'"{comment.content}"\n'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[review_author.email],
        fail_silently=True,
    )
