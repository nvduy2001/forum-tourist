from django.contrib import admin
from django.utils import timezone

from .models import MenuItem, Place, PlaceImage, PlaceOwnershipRequest, PlacePromotion, PlaceSearchLog
from .tasks import send_ownership_request_result_email


class PlaceImageInline(admin.TabularInline):
    model = PlaceImage
    extra = 0


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'category', 'status', 'review_count')
    list_filter = ('status', 'region', 'category')
    search_fields = ('name', 'address')
    readonly_fields = ('review_count',)
    inlines = [PlaceImageInline, MenuItemInline]


@admin.register(PlacePromotion)
class PlacePromotionAdmin(admin.ModelAdmin):
    list_display = ('title', 'place', 'status', 'created_at')
    list_filter = ('status',)
    actions = ['approve_promotions', 'reject_promotions']

    @admin.action(description='Duyệt tin khuyến mãi')
    def approve_promotions(self, request, queryset):
        queryset.update(status=PlacePromotion.Status.APPROVED)

    @admin.action(description='Từ chối tin khuyến mãi')
    def reject_promotions(self, request, queryset):
        queryset.update(status=PlacePromotion.Status.REJECTED)


@admin.register(PlaceSearchLog)
class PlaceSearchLogAdmin(admin.ModelAdmin):
    list_display = ('query', 'created_at')
    readonly_fields = ('query', 'created_at')


@admin.register(PlaceOwnershipRequest)
class PlaceOwnershipRequestAdmin(admin.ModelAdmin):
    list_display = ('place', 'user', 'contact_name', 'contact_phone', 'status', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('place', 'user', 'contact_name', 'contact_phone', 'contact_email', 'note', 'created_at')
    actions = ['approve_requests', 'reject_requests']

    @admin.action(description='Duyệt yêu cầu (gắn business owner + đặt place verified)')
    def approve_requests(self, request, queryset):
        for ownership_request in queryset.filter(status=PlaceOwnershipRequest.Status.PENDING):
            ownership_request.status = PlaceOwnershipRequest.Status.APPROVED
            ownership_request.reviewed_by = request.user
            ownership_request.reviewed_at = timezone.now()
            ownership_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

            owner = ownership_request.user
            owner.is_business_owner = True
            owner.owned_place = ownership_request.place
            owner.save(update_fields=['is_business_owner', 'owned_place'])

            ownership_request.place.status = Place.Status.VERIFIED
            ownership_request.place.save(update_fields=['status'])

            send_ownership_request_result_email.delay(ownership_request.id)

    @admin.action(description='Từ chối yêu cầu')
    def reject_requests(self, request, queryset):
        for ownership_request in queryset.filter(status=PlaceOwnershipRequest.Status.PENDING):
            ownership_request.status = PlaceOwnershipRequest.Status.REJECTED
            ownership_request.reviewed_by = request.user
            ownership_request.reviewed_at = timezone.now()
            ownership_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

            send_ownership_request_result_email.delay(ownership_request.id)
