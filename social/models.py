from django.conf import settings
from django.db import models


class UserFollow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following'
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'following'], name='unique_user_follow'),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F('following')), name='user_cannot_follow_self'
            ),
        ]

    def __str__(self):
        return f'{self.follower} follows {self.following}'


class PlaceFollow(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followed_places')
    place = models.ForeignKey('places.Place', on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'place'], name='unique_place_follow'),
        ]

    def __str__(self):
        return f'{self.user} follows {self.place}'


class ReviewVote(models.Model):
    """Vote 'hữu ích' cho một đánh giá."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_votes')
    review = models.ForeignKey('reviews.Review', on_delete=models.CASCADE, related_name='helpful_votes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'review'], name='unique_review_vote'),
        ]

    def __str__(self):
        return f'{self.user} voted helpful on {self.review_id}'


class CommentLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comment_likes')
    comment = models.ForeignKey('reviews.Comment', on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'comment'], name='unique_comment_like'),
        ]

    def __str__(self):
        return f'{self.user} likes comment {self.comment_id}'
