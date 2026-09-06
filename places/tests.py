from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase
from django.urls import reverse

from reviews.models import Review

from .models import (
    MenuItem, Place, PlaceImage, PlaceOpeningHour, PlaceOwnershipRequest, PlacePromotion, PlaceSearchLog,
)
from .views import PlaceListView

User = get_user_model()


class PlaceBusinessCategoryTests(TestCase):
    def test_food_is_business_category(self):
        place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.assertTrue(place.is_business_category)

    def test_scenic_spot_is_not_business_category(self):
        place = Place.objects.create(
            name='Núi B', address='456 Y', region='Đà Lạt', category='scenic_spot',
            latitude=11.9, longitude=108.4,
        )
        self.assertFalse(place.is_business_category)


class PlaceSearchFilterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.hanoi_food = Place.objects.create(
            name='Phở Hà Nội', address='1 Láng', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.hanoi_cafe = Place.objects.create(
            name='Cafe Hà Nội', address='2 Láng', region='Hà Nội', category='cafe',
            latitude=21.01, longitude=105.81,
        )
        self.danang_food = Place.objects.create(
            name='Mì Quảng Đà Nẵng', address='3 Bạch Đằng', region='Đà Nẵng', category='food',
            latitude=16.0, longitude=108.2,
        )

    def _get_queryset(self, **params):
        request = self.factory.get('/places/', params)
        view = PlaceListView()
        view.request = request
        return list(view.get_queryset())

    def test_filter_by_region(self):
        results = self._get_queryset(region='Hà Nội')
        self.assertCountEqual(results, [self.hanoi_food, self.hanoi_cafe])

    def test_filter_by_category(self):
        results = self._get_queryset(category='food')
        self.assertCountEqual(results, [self.hanoi_food, self.danang_food])

    def test_filter_by_region_and_category(self):
        results = self._get_queryset(region='Hà Nội', category='food')
        self.assertEqual(results, [self.hanoi_food])

    def test_search_by_name_query(self):
        results = self._get_queryset(q='Quảng')
        self.assertEqual(results, [self.danang_food])

    def test_no_filters_returns_all(self):
        results = self._get_queryset()
        self.assertEqual(len(results), 3)


class PlaceCreateTests(TestCase):
    def test_new_place_defaults_to_pending_verification(self):
        user = User.objects.create_user(username='u1', password='pass12345')
        self.client.force_login(user)
        response = self.client.post(reverse('places:place_create'), {
            'name': 'Địa điểm mới', 'description': '', 'address': 'Đâu đó',
            'region': 'Hà Nội', 'category': 'food', 'latitude': '21.0', 'longitude': '105.8',
        })
        self.assertEqual(response.status_code, 302)
        place = Place.objects.get(name='Địa điểm mới')
        self.assertEqual(place.status, Place.Status.PENDING_VERIFICATION)


class PlaceUpdatePermissionTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.owner = User.objects.create_user(
            username='owner', password='pass12345', is_business_owner=True, owned_place=self.place,
        )
        self.other = User.objects.create_user(username='other', password='pass12345')

    def test_non_owner_cannot_access_update(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse('places:place_update', args=[self.place.id]))
        self.assertEqual(response.status_code, 403)

    def test_owner_can_submit_update(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('places:place_update', args=[self.place.id]), {
            'name': 'Quán A (đã sửa)', 'description': '', 'address': '123 X',
            'region': 'Hà Nội', 'category': 'food', 'latitude': '21.0', 'longitude': '105.8',
        })
        self.assertEqual(response.status_code, 302)
        self.place.refresh_from_db()
        self.assertEqual(self.place.name, 'Quán A (đã sửa)')


class PlaceOwnershipRequestTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.claimant = User.objects.create_user(
            username='claimant', password='pass12345', email='claimant@example.com',
        )
        self.admin_user = User.objects.create_superuser(
            username='admin', password='pass12345', email='admin@example.com',
        )
        self.factory = RequestFactory()

    def _submit_request(self):
        self.client.force_login(self.claimant)
        return self.client.post(reverse('places:request_ownership', args=[self.place.id]), {
            'contact_name': 'Nguyễn Văn A',
            'contact_phone': '0900000000',
            'contact_email': 'claimant@example.com',
            'note': 'Tôi là chủ quán này',
        })

    def test_submit_creates_pending_request(self):
        response = self._submit_request()
        self.assertEqual(response.status_code, 302)
        req = PlaceOwnershipRequest.objects.get(place=self.place, user=self.claimant)
        self.assertEqual(req.status, PlaceOwnershipRequest.Status.PENDING)

    def test_duplicate_pending_request_not_created(self):
        self._submit_request()
        self._submit_request()
        self.assertEqual(
            PlaceOwnershipRequest.objects.filter(place=self.place, user=self.claimant).count(), 1
        )

    def test_cannot_claim_ownership_of_attraction_place(self):
        attraction = Place.objects.create(
            name='Thác Bản Giốc', address='Cao Bằng', region='Cao Bằng', category='scenic_spot',
            latitude=22.8, longitude=106.7,
        )
        self.client.force_login(self.claimant)
        response = self.client.post(reverse('places:request_ownership', args=[attraction.id]), {
            'contact_name': 'Nguyễn Văn A', 'contact_phone': '0900000000',
            'contact_email': 'claimant@example.com', 'note': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PlaceOwnershipRequest.objects.filter(place=attraction).exists())

    def _admin_request(self):
        request = self.factory.get('/admin/')
        request.user = self.admin_user
        return request

    def test_approve_grants_business_owner_and_verifies_place(self):
        self._submit_request()
        req = PlaceOwnershipRequest.objects.get(place=self.place, user=self.claimant)
        model_admin = django_admin.site._registry[PlaceOwnershipRequest]

        mail.outbox = []
        model_admin.approve_requests(self._admin_request(), PlaceOwnershipRequest.objects.filter(pk=req.pk))

        req.refresh_from_db()
        self.claimant.refresh_from_db()
        self.place.refresh_from_db()

        self.assertEqual(req.status, PlaceOwnershipRequest.Status.APPROVED)
        self.assertTrue(self.claimant.is_business_owner)
        self.assertEqual(self.claimant.owned_place_id, self.place.id)
        self.assertEqual(self.place.status, Place.Status.VERIFIED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.claimant.email, mail.outbox[0].to)

    def test_reject_marks_rejected_and_notifies(self):
        self._submit_request()
        req = PlaceOwnershipRequest.objects.get(place=self.place, user=self.claimant)
        model_admin = django_admin.site._registry[PlaceOwnershipRequest]

        mail.outbox = []
        model_admin.reject_requests(self._admin_request(), PlaceOwnershipRequest.objects.filter(pk=req.pk))

        req.refresh_from_db()
        self.claimant.refresh_from_db()

        self.assertEqual(req.status, PlaceOwnershipRequest.Status.REJECTED)
        self.assertFalse(self.claimant.is_business_owner)
        self.assertEqual(len(mail.outbox), 1)


class PlaceListAdvancedFilterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        # Hà Nội trung tâm
        self.near = Place.objects.create(
            name='Gần', address='1 X', region='Hà Nội', category='food',
            latitude=21.0285, longitude=105.8542,
        )
        # Đà Nẵng, cách xa Hà Nội hàng trăm km
        self.far = Place.objects.create(
            name='Xa', address='2 X', region='Đà Nẵng', category='food',
            latitude=16.0544, longitude=108.2022,
        )
        self.reviewer = User.objects.create_user(username='reviewer', password='pass12345')
        Review.objects.create(place=self.near, user=self.reviewer, rating=5, content='Tốt')
        Review.objects.create(place=self.far, user=self.reviewer, rating=2, content='Tệ')

    def _get_queryset(self, **params):
        request = self.factory.get('/places/', params)
        view = PlaceListView()
        view.request = request
        return list(view.get_queryset())

    def test_distance_filter_excludes_far_place(self):
        results = self._get_queryset(lat='21.0285', lng='105.8542', radius_km='50')
        self.assertEqual(results, [self.near])

    def test_min_rating_filter(self):
        results = self._get_queryset(min_rating='4')
        self.assertEqual(results, [self.near])

    def test_search_logs_query(self):
        self._get_queryset(q='Gần')
        self.assertTrue(PlaceSearchLog.objects.filter(query='Gần').exists())


class PlaceOwnerManagementTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.owner = User.objects.create_user(
            username='owner', password='pass12345', is_business_owner=True, owned_place=self.place,
        )
        self.other = User.objects.create_user(username='other', password='pass12345')

    def test_owner_can_add_menu_item(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('places:add_menu_item', args=[self.place.pk]), {
            'name': 'Phở', 'price': '50000',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MenuItem.objects.filter(place=self.place, name='Phở').count(), 1)

    def test_non_owner_cannot_add_menu_item(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('places:add_menu_item', args=[self.place.pk]), {
            'name': 'Phở', 'price': '50000',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(MenuItem.objects.count(), 0)

    def test_non_owner_cannot_delete_menu_item(self):
        item = MenuItem.objects.create(place=self.place, name='Phở', price=50000)
        self.client.force_login(self.other)
        response = self.client.get(reverse('places:delete_menu_item', args=[self.place.pk, item.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(MenuItem.objects.filter(pk=item.pk).exists())

    def test_owner_promotion_pending_until_approved(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('places:create_promotion', args=[self.place.pk]), {
            'title': 'Giảm giá 20%', 'content': 'Áp dụng cuối tuần',
        })
        promo = PlacePromotion.objects.get(place=self.place)
        self.assertEqual(promo.status, PlacePromotion.Status.PENDING)

        response = self.client.get(reverse('places:place_detail', args=[self.place.pk]))
        self.assertNotContains(response, 'Giảm giá 20%')

        promo.status = PlacePromotion.Status.APPROVED
        promo.save(update_fields=['status'])
        response = self.client.get(reverse('places:place_detail', args=[self.place.pk]))
        self.assertContains(response, 'Giảm giá 20%')

    def _place_update_data(self, **opening_hours_data):
        return {
            'name': 'Quán A', 'description': '', 'address': '123 X', 'region': 'Hà Nội',
            'category': 'food', 'latitude': '21.0', 'longitude': '105.8', 'google_maps_url': '',
            **opening_hours_data,
        }

    def test_owner_can_set_opening_hours_via_place_update(self):
        self.client.force_login(self.owner)
        data = self._place_update_data()
        for value, _label in PlaceOpeningHour.Weekday.choices:
            if value == PlaceOpeningHour.Weekday.SUNDAY:
                data[f'closed_{value}'] = 'on'
            else:
                data[f'open_{value}'] = '08:00'
                data[f'close_{value}'] = '22:00'

        response = self.client.post(reverse('places:place_update', args=[self.place.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PlaceOpeningHour.objects.filter(place=self.place).count(), 7)

        sunday = PlaceOpeningHour.objects.get(place=self.place, weekday=PlaceOpeningHour.Weekday.SUNDAY)
        self.assertTrue(sunday.is_closed)
        monday = PlaceOpeningHour.objects.get(place=self.place, weekday=PlaceOpeningHour.Weekday.MONDAY)
        self.assertFalse(monday.is_closed)
        self.assertEqual(str(monday.open_time), '08:00:00')

    def test_non_owner_cannot_set_opening_hours(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse('places:place_update', args=[self.place.pk]), self._place_update_data()
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(PlaceOpeningHour.objects.filter(place=self.place).count(), 0)

    def test_opening_hours_set_when_creating_place(self):
        self.client.force_login(self.owner)
        data = {
            'name': 'Quán B', 'description': '', 'address': '456 Y', 'region': 'Hà Nội',
            'category': 'cafe', 'latitude': '21.1', 'longitude': '105.9', 'google_maps_url': '',
            'open_0': '07:00', 'close_0': '21:00',
        }
        response = self.client.post(reverse('places:place_create'), data)
        self.assertEqual(response.status_code, 302)

        new_place = Place.objects.get(name='Quán B')
        monday = PlaceOpeningHour.objects.get(place=new_place, weekday=PlaceOpeningHour.Weekday.MONDAY)
        self.assertEqual(str(monday.open_time), '07:00:00')
