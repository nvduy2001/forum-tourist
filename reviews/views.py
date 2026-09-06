import mimetypes

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Avg
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic import DeleteView, UpdateView
from django_ratelimit.decorators import ratelimit

from places.models import Place

from .forms import ReviewForm
from .models import CheckIn, Comment, Review, ReviewMedia, ReviewTag
from .utils import haversine_distance_m


@login_required
def write_review_page(request, place_id):
    """Trang viết đánh giá (time capsule review): KHÔNG truyền điểm trung bình / review khác
    của địa điểm vào context — chỉ hiện sau khi submit thành công qua JS gọi write_review()."""
    place = get_object_or_404(Place, pk=place_id)
    return render(request, 'reviews/write_review.html', {
        'place': place,
        'tags': ReviewTag.objects.all(),
        'checkin_threshold_m': settings.CHECKIN_DISTANCE_THRESHOLD_M,
    })


@login_required
@require_http_methods(['POST'])
@ratelimit(key='user', rate='10/m', block=True)
def write_review(request, place_id):
    """Time capsule review: response chỉ chứa review vừa tạo, KHÔNG kèm điểm trung bình / review
    khác của địa điểm. Chỉ sau khi POST thành công mới trả so sánh điểm cá nhân vs trung bình cộng đồng."""
    place = get_object_or_404(Place, pk=place_id)

    form = ReviewForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors}, status=400)

    review = form.save(commit=False)
    review.place = place
    review.user = request.user
    review.save()
    form.save_m2m()

    for uploaded_file in request.FILES.getlist('media'):
        content_type, _ = mimetypes.guess_type(uploaded_file.name)
        media_type = ReviewMedia.MediaType.VIDEO if content_type and content_type.startswith('video') else ReviewMedia.MediaType.IMAGE
        ReviewMedia.objects.create(review=review, file=uploaded_file, media_type=media_type)

    community_average = place.reviews.aggregate(avg=Avg('rating'))['avg']
    return JsonResponse({
        'review_id': review.id,
        'personal_rating': review.rating,
        'community_average': round(community_average, 2) if community_average is not None else None,
    })


class ReviewEditableRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Chỉ tác giả sửa/xóa được, và chỉ trong 24h kể từ khi tạo."""

    model = Review

    def test_func(self):
        review = self.get_object()
        return review.user_id == self.request.user.id and review.is_editable


class ReviewUpdateView(ReviewEditableRequiredMixin, UpdateView):
    fields = ['rating', 'quality_rating', 'price_rating', 'service_rating', 'space_rating', 'content', 'tags']

    def get_success_url(self):
        return reverse('places:place_detail', args=[self.object.place_id])


class ReviewDeleteView(ReviewEditableRequiredMixin, DeleteView):
    def get_success_url(self):
        return reverse('places:place_detail', args=[self.object.place_id])


@login_required
@require_http_methods(['POST'])
def check_in(request, place_id):
    """Check-in xác thực đánh giá: so khoảng cách GPS (Haversine) với tọa độ địa điểm."""
    place = get_object_or_404(Place, pk=place_id)

    try:
        latitude = float(request.POST['latitude'])
        longitude = float(request.POST['longitude'])
    except (KeyError, ValueError):
        return JsonResponse({'error': 'invalid coordinates'}, status=400)

    distance_m = haversine_distance_m(latitude, longitude, place.latitude, place.longitude)
    is_valid = distance_m <= settings.CHECKIN_DISTANCE_THRESHOLD_M

    check_in = CheckIn.objects.create(
        user=request.user,
        place=place,
        latitude=latitude,
        longitude=longitude,
        distance_m=distance_m,
        is_valid=is_valid,
    )

    return JsonResponse({
        'is_valid': check_in.is_valid,
        'distance_m': round(check_in.distance_m, 1),
        'threshold_m': settings.CHECKIN_DISTANCE_THRESHOLD_M,
    })


@login_required
@require_http_methods(['POST'])
@ratelimit(key='user', rate='20/m', block=True)
def add_comment(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'content required'}, status=400)

    parent = None
    parent_id = request.POST.get('parent_id')
    if parent_id:
        parent = get_object_or_404(Comment, pk=parent_id, review=review)

    comment = Comment.objects.create(review=review, user=request.user, content=content, parent=parent)
    return JsonResponse({
        'comment_id': comment.id,
        'username': request.user.username,
        'content': comment.content,
        'parent_id': parent.id if parent else None,
    })


@login_required
@require_http_methods(['POST'])
def reply_as_owner(request, review_id):
    """Chủ địa điểm phản hồi công khai một đánh giá."""
    review = get_object_or_404(Review, pk=review_id)
    if not (request.user.is_business_owner and request.user.owned_place_id == review.place_id):
        return HttpResponseForbidden('Bạn không phải chủ địa điểm này.')

    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'content required'}, status=400)

    from django.utils import timezone

    review.owner_reply = content
    review.owner_reply_at = timezone.now()
    review.save(update_fields=['owner_reply', 'owner_reply_at'])

    return JsonResponse({'owner_reply': review.owner_reply, 'owner_reply_at': review.owner_reply_at.isoformat()})
