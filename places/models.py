from django.conf import settings
from django.db import models


class Place(models.Model):
    class Status(models.TextChoices):
        PENDING_VERIFICATION = 'pending_verification', 'Pending verification'
        VERIFIED = 'verified', 'Verified'

    class Category(models.TextChoices):
        # Cơ sở kinh doanh — có chủ sở hữu thật, dùng được công cụ quản lý (menu/giờ mở cửa/khuyến mãi)
        FOOD = 'food', 'Nhà hàng / Ẩm thực'
        CAFE = 'cafe', 'Quán cà phê'
        BEVERAGE = 'beverage', 'Quán nước / Đồ uống'
        HOTEL = 'hotel', 'Khách sạn / Lưu trú'
        SHOP = 'shop', 'Cửa hàng'
        # Địa điểm du lịch — không thuộc sở hữu tư nhân, không có luồng xác minh chủ sở hữu
        SCENIC_SPOT = 'scenic_spot', 'Danh lam thắng cảnh'
        HISTORICAL_SITE = 'historical_site', 'Di tích lịch sử'
        BEACH = 'beach', 'Bãi biển'
        MUSEUM = 'museum', 'Bảo tàng'

    BUSINESS_CATEGORIES = {Category.FOOD, Category.CAFE, Category.BEVERAGE, Category.HOTEL, Category.SHOP}

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)
    region = models.CharField(max_length=100)
    category = models.CharField(max_length=30, choices=Category.choices)

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    # Link Google Maps dán tay — OSM/Nominatim không có đầy đủ dữ liệu cửa hàng như Google Maps
    google_maps_url = models.URLField(
        blank=True,
        help_text='Dán link Google Maps của địa điểm (mở app Google Maps, bấm Chia sẻ → Sao chép liên kết).',
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_VERIFICATION,
    )

    # Đếm sẵn (denormalized) — cập nhật qua signal ở app reviews, không tự tính lại bằng aggregate mỗi request
    review_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_business_category(self):
        """Chỉ cơ sở kinh doanh mới có chủ sở hữu thật — địa điểm du lịch không dùng luồng xác minh chủ sở hữu."""
        return self.category in {c.value for c in self.BUSINESS_CATEGORIES}


class PlaceOpeningHour(models.Model):
    """Giờ mở cửa theo từng ngày trong tuần (T2-CN), giống bảng giờ mở cửa của Google Maps."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, 'Thứ 2'
        TUESDAY = 1, 'Thứ 3'
        WEDNESDAY = 2, 'Thứ 4'
        THURSDAY = 3, 'Thứ 5'
        FRIDAY = 4, 'Thứ 6'
        SATURDAY = 5, 'Thứ 7'
        SUNDAY = 6, 'Chủ nhật'

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='opening_hours')
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    is_closed = models.BooleanField(default=False)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ['weekday']
        constraints = [
            models.UniqueConstraint(fields=['place', 'weekday'], name='unique_place_weekday'),
        ]

    def __str__(self):
        return f'{self.place} - {self.get_weekday_display()}'


class PlaceImage(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='places/')
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f'Image for {self.place}'


class MenuItem(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=0)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.name} ({self.place})'


class PlacePromotion(models.Model):
    """Chủ địa điểm đăng khuyến mãi/tin tức — cần Admin kiểm duyệt trước khi hiển thị công khai."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='promotions')
    title = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class PlaceSearchLog(models.Model):
    """Ghi lại từ khóa tìm kiếm để Admin xem xu hướng tìm kiếm."""

    query = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query


class PlaceOwnershipRequest(models.Model):
    """Xác minh chủ địa điểm: user điền form liên hệ, Admin đối chiếu thủ công rồi duyệt/từ chối."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='ownership_requests')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ownership_requests'
    )

    contact_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=30)
    contact_email = models.EmailField()
    note = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ownership_requests_reviewed',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} -> {self.place} ({self.status})'
