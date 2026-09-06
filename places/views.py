from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Avg, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from reviews.utils import haversine_distance_m
from social.models import PlaceFollow

from .forms import PlaceOwnershipRequestForm
from .models import (
    MenuItem, Place, PlaceImage, PlaceOpeningHour, PlaceOwnershipRequest, PlacePromotion, PlaceSearchLog,
)

PLACE_FIELDS = [
    'name', 'description', 'address', 'region', 'category', 'latitude', 'longitude', 'google_maps_url',
]


def _owner_of(place, user):
    return user.is_authenticated and user.is_business_owner and user.owned_place_id == place.id


def _opening_hours_days(place=None):
    """7 dòng T2-CN, lấy dữ liệu đã lưu nếu có (dùng để đổ vào form khi sửa)."""
    existing = {h.weekday: h for h in PlaceOpeningHour.objects.filter(place=place)} if place else {}
    return [
        existing.get(value, PlaceOpeningHour(place=place, weekday=value))
        for value, _label in PlaceOpeningHour.Weekday.choices
    ]


def _save_opening_hours(place, post_data):
    for value, _label in PlaceOpeningHour.Weekday.choices:
        hour, _ = PlaceOpeningHour.objects.get_or_create(place=place, weekday=value)
        hour.is_closed = post_data.get(f'closed_{value}') == 'on'
        hour.open_time = post_data.get(f'open_{value}', '').strip() or None
        hour.close_time = post_data.get(f'close_{value}', '').strip() or None
        hour.save()


class PlaceListView(ListView):
    model = Place
    context_object_name = 'places'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category_choices'] = Place.Category.choices
        return context

    def get_queryset(self):
        queryset = Place.objects.annotate(avg_rating=Avg('reviews__rating')).prefetch_related('images')
        region = self.request.GET.get('region')
        category = self.request.GET.get('category')
        query = self.request.GET.get('q')
        min_rating = self.request.GET.get('min_rating')
        sort = self.request.GET.get('sort', 'popular')

        if region:
            queryset = queryset.filter(region__iexact=region)
        if category:
            queryset = queryset.filter(category__iexact=category)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(address__icontains=query))
            PlaceSearchLog.objects.create(query=query)
        if min_rating:
            try:
                queryset = queryset.filter(avg_rating__gte=float(min_rating))
            except ValueError:
                pass

        if sort == 'rating':
            queryset = queryset.order_by('-avg_rating')
        else:
            queryset = queryset.order_by('-review_count')

        return self._filter_by_distance(queryset)

    def _filter_by_distance(self, queryset):
        lat = self.request.GET.get('lat')
        lng = self.request.GET.get('lng')
        radius_km = self.request.GET.get('radius_km')
        if not (lat and lng and radius_km):
            return queryset

        try:
            lat, lng, radius_m = float(lat), float(lng), float(radius_km) * 1000
        except ValueError:
            return queryset

        nearby_ids = [
            place.id for place in queryset
            if haversine_distance_m(lat, lng, place.latitude, place.longitude) <= radius_m
        ]
        return Place.objects.filter(id__in=nearby_ids).annotate(
            avg_rating=Avg('reviews__rating')
        ).prefetch_related('images')


class PlaceDetailView(DetailView):
    model = Place
    context_object_name = 'place'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        place = self.object
        user = self.request.user

        reviews = place.reviews.select_related('user').prefetch_related('media', 'tags')
        if not (user.is_authenticated and user.is_staff):
            reviews = reviews.filter(is_hidden=False)

        context['reviews'] = reviews
        context['average_rating'] = place.reviews.filter(is_hidden=False).aggregate(avg=Avg('rating'))['avg']
        context['opening_hours'] = place.opening_hours.all()
        context['images'] = place.images.all()
        context['menu_items'] = place.menu_items.all()
        context['promotions'] = place.promotions.filter(status=PlacePromotion.Status.APPROVED)
        context['is_owner'] = _owner_of(place, user)

        if user.is_authenticated:
            context['is_following_place'] = PlaceFollow.objects.filter(user=user, place=place).exists()

        return context


class PlaceCreateView(LoginRequiredMixin, CreateView):
    model = Place
    fields = PLACE_FIELDS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['days'] = _opening_hours_days()
        return context

    def form_valid(self, form):
        # Địa điểm mới luôn ở trạng thái chờ duyệt, Admin đối chiếu thủ công rồi mới verified
        form.instance.status = Place.Status.PENDING_VERIFICATION
        response = super().form_valid(form)
        _save_opening_hours(self.object, self.request.POST)
        return response

    def get_success_url(self):
        return reverse('places:place_detail', args=[self.object.pk])


class PlaceOwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        place = self.get_object()
        return _owner_of(place, self.request.user)


class PlaceUpdateView(PlaceOwnerRequiredMixin, UpdateView):
    model = Place
    fields = PLACE_FIELDS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['days'] = _opening_hours_days(self.object)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        _save_opening_hours(self.object, self.request.POST)
        return response

    def get_success_url(self):
        return reverse('places:place_detail', args=[self.object.pk])


@login_required
def request_ownership(request, place_id):
    """User điền form liên hệ để yêu cầu xác minh là chủ địa điểm; Admin duyệt thủ công qua admin.
    Chỉ áp dụng cho địa điểm thuộc nhóm cơ sở kinh doanh — địa điểm du lịch không có chủ sở hữu tư nhân."""
    place = get_object_or_404(Place, pk=place_id)
    if not place.is_business_category:
        messages.error(request, 'Địa điểm du lịch không có chủ sở hữu để xác minh.')
        return redirect('places:place_detail', pk=place.pk)

    if request.method == 'POST':
        form = PlaceOwnershipRequestForm(request.POST)
        if form.is_valid():
            already_pending = PlaceOwnershipRequest.objects.filter(
                place=place, user=request.user, status=PlaceOwnershipRequest.Status.PENDING
            ).exists()
            if already_pending:
                messages.info(request, 'Bạn đã có một yêu cầu đang chờ duyệt cho địa điểm này.')
            else:
                ownership_request = form.save(commit=False)
                ownership_request.place = place
                ownership_request.user = request.user
                ownership_request.save()
                messages.success(request, 'Đã gửi yêu cầu xác minh, Admin sẽ đối chiếu và phản hồi qua email.')
            return redirect('places:place_detail', pk=place.pk)
    else:
        form = PlaceOwnershipRequestForm()

    return render(request, 'places/request_ownership.html', {'place': place, 'form': form})


def _require_owner(request, place):
    if not _owner_of(place, request.user):
        return HttpResponseForbidden('Bạn không phải chủ địa điểm này.')
    return None


@login_required
def add_place_image(request, place_id):
    place = get_object_or_404(Place, pk=place_id)
    denied = _require_owner(request, place)
    if denied:
        return denied

    if request.method == 'POST' and request.FILES.get('image'):
        PlaceImage.objects.create(
            place=place, image=request.FILES['image'], caption=request.POST.get('caption', '')
        )
    return redirect('places:place_detail', pk=place.pk)


@login_required
def delete_place_image(request, place_id, image_id):
    place = get_object_or_404(Place, pk=place_id)
    denied = _require_owner(request, place)
    if denied:
        return denied

    PlaceImage.objects.filter(pk=image_id, place=place).delete()
    return redirect('places:place_detail', pk=place.pk)


@login_required
def add_menu_item(request, place_id):
    place = get_object_or_404(Place, pk=place_id)
    denied = _require_owner(request, place)
    if denied:
        return denied

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        price = request.POST.get('price', '').strip()
        if name and price:
            MenuItem.objects.create(
                place=place, name=name, price=price, description=request.POST.get('description', '')
            )
    return redirect('places:place_detail', pk=place.pk)


@login_required
def delete_menu_item(request, place_id, item_id):
    place = get_object_or_404(Place, pk=place_id)
    denied = _require_owner(request, place)
    if denied:
        return denied

    MenuItem.objects.filter(pk=item_id, place=place).delete()
    return redirect('places:place_detail', pk=place.pk)


@login_required
def create_promotion(request, place_id):
    """Chủ địa điểm đăng khuyến mãi/tin tức — luôn ở trạng thái chờ Admin kiểm duyệt."""
    place = get_object_or_404(Place, pk=place_id)
    denied = _require_owner(request, place)
    if denied:
        return denied

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if title and content:
            PlacePromotion.objects.create(place=place, title=title, content=content)
            messages.success(request, 'Đã gửi tin, chờ Admin kiểm duyệt trước khi hiển thị công khai.')
    return redirect('places:place_detail', pk=place.pk)
