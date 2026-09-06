from django.conf import settings
from django.db import models
from django.urls import reverse


class ForumPost(models.Model):
    class Category(models.TextChoices):
        TRAVEL_EXPERIENCE = 'kinh_nghiem_du_lich', 'Kinh nghiệm du lịch'
        SERVICE_QA = 'hoi_dap_dich_vu', 'Hỏi đáp dịch vụ'
        OTHER = 'khac', 'Khác'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_posts')
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('forum:post_detail', args=[self.pk])
