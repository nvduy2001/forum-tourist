from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import PlaceFollow, ReviewVote, UserFollow


@shared_task
def send_new_follower_email(follow_id):
    try:
        follow = UserFollow.objects.select_related('follower', 'following').get(pk=follow_id)
    except UserFollow.DoesNotExist:
        return

    followed = follow.following
    if not followed.email:
        return

    send_mail(
        subject=f'{follow.follower.username} vừa theo dõi bạn',
        message=f'Chào {followed.username},\n\n{follow.follower.username} vừa bắt đầu theo dõi bạn trên Forum Tourist.\n',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[followed.email],
        fail_silently=True,
    )


@shared_task
def send_helpful_vote_email(vote_id):
    try:
        vote = ReviewVote.objects.select_related('user', 'review__user', 'review__place').get(pk=vote_id)
    except ReviewVote.DoesNotExist:
        return

    review_author = vote.review.user
    if vote.user_id == review_author.id or not review_author.email:
        return

    send_mail(
        subject=f'Đánh giá của bạn về "{vote.review.place.name}" vừa được vote hữu ích',
        message=(
            f'Chào {review_author.username},\n\n'
            f'{vote.user.username} vừa đánh giá đánh giá của bạn về "{vote.review.place.name}" là hữu ích.\n'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[review_author.email],
        fail_silently=True,
    )


@shared_task
def notify_place_followers_of_new_review(review_id):
    from reviews.models import Review

    try:
        review = Review.objects.select_related('place', 'user').get(pk=review_id)
    except Review.DoesNotExist:
        return

    follower_emails = list(
        PlaceFollow.objects.filter(place_id=review.place_id)
        .exclude(user_id=review.user_id)
        .exclude(user__email='')
        .values_list('user__email', flat=True)
    )
    if not follower_emails:
        return

    send_mail(
        subject=f'Có đánh giá mới cho "{review.place.name}"',
        message=(
            f'{review.user.username} vừa đánh giá {review.rating}/5 sao cho "{review.place.name}" '
            f'mà bạn đang theo dõi.\n'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=follower_emails,
        fail_silently=True,
    )
