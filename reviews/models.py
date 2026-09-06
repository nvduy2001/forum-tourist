from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from places.models import Place

EDIT_WINDOW = timedelta(hours=24)

RATING_VALIDATORS = [MinValueValidator(1), MaxValueValidator(5)]


class ReviewTag(models.Model):
    """Thẻ cảm xúc/từ khóa nhanh, vd 'đáng tiền', 'phục vụ chậm'."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Review(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    # Điểm theo từng tiêu chí con — tùy chọn, bổ sung cho điểm tổng thể ở trên
    quality_rating = models.PositiveSmallIntegerField(null=True, blank=True, validators=RATING_VALIDATORS)
    price_rating = models.PositiveSmallIntegerField(null=True, blank=True, validators=RATING_VALIDATORS)
    service_rating = models.PositiveSmallIntegerField(null=True, blank=True, validators=RATING_VALIDATORS)
    space_rating = models.PositiveSmallIntegerField(null=True, blank=True, validators=RATING_VALIDATORS)

    content = models.TextField()
    tags = models.ManyToManyField(ReviewTag, blank=True, related_name='reviews')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Chủ địa điểm phản hồi công khai
    owner_reply = models.TextField(blank=True)
    owner_reply_at = models.DateTimeField(null=True, blank=True)

    # Admin ẩn nội dung vi phạm mà không xóa hẳn (khôi phục được)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} -> {self.place} ({self.rating} sao)'

    @property
    def is_editable(self):
        """User chỉ được sửa/xóa đánh giá của mình trong 24h kể từ khi tạo."""
        return timezone.now() - self.created_at <= EDIT_WINDOW


class ReviewMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='review_media/')
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.media_type} for review {self.review_id}'


class Comment(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.user} on review {self.review_id}'


class CheckIn(models.Model):
    """Check-in xác thực đánh giá bằng Geolocation API (frontend) + Haversine (ngưỡng CHECKIN_DISTANCE_THRESHOLD_M)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='check_ins')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='check_ins')
    review = models.OneToOneField(
        Review, on_delete=models.CASCADE, related_name='check_in', null=True, blank=True
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    distance_m = models.FloatField()
    is_valid = models.BooleanField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} @ {self.place} ({self.distance_m:.0f}m, valid={self.is_valid})'
