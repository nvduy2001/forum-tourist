from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from places.models import Place, PlaceSearchLog
from reviews.models import Review

from .models import Report

User = get_user_model()


@login_required
@require_POST
def create_report(request):
    """Người dùng báo cáo nội dung vi phạm (review, comment, forum post, place).
    Kiểm duyệt (Admin với quyền hẹp hơn) xử lý báo cáo qua Django admin, không có model Role riêng."""
    app_label = request.POST.get('app_label')
    model = request.POST.get('model')
    object_id = request.POST.get('object_id')
    reason = request.POST.get('reason', '').strip()

    if not (app_label and model and object_id and reason):
        return JsonResponse({'error': 'missing fields'}, status=400)

    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model)
    except ContentType.DoesNotExist:
        return JsonResponse({'error': 'invalid content type'}, status=400)

    report = Report.objects.create(
        reporter=request.user,
        content_type=content_type,
        object_id=object_id,
        reason=reason,
    )
    return JsonResponse({'report_id': report.id})


@staff_member_required
def dashboard(request):
    """Thống kê hệ thống cho Admin: user mới, review mới, địa điểm nổi bật, xu hướng tìm kiếm."""
    now = timezone.now()
    last_7d = now - timezone.timedelta(days=7)
    last_30d = now - timezone.timedelta(days=30)

    context = {
        'new_users_7d': User.objects.filter(date_joined__gte=last_7d).count(),
        'new_users_30d': User.objects.filter(date_joined__gte=last_30d).count(),
        'new_reviews_7d': Review.objects.filter(created_at__gte=last_7d).count(),
        'new_reviews_30d': Review.objects.filter(created_at__gte=last_30d).count(),
        'top_places': Place.objects.order_by('-review_count')[:10],
        'top_searches': (
            PlaceSearchLog.objects.filter(created_at__gte=last_30d)
            .values('query')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        ),
        'pending_reports': Report.objects.filter(status=Report.Status.PENDING).count(),
    }
    return render(request, 'moderation/dashboard.html', context)
