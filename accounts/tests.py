from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase
from django.urls import reverse

from places.models import Place
from reviews.models import Review

User = get_user_model()


class ProfileDetailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        Review.objects.create(place=self.place, user=self.user, rating=5, content='Tốt')

    def test_profile_shows_review_count_and_tier(self):
        response = self.client.get(reverse('accounts:profile_detail', args=[self.user.username]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['review_count'], 1)
        self.assertContains(response, 'Người mới')


class ProfileUpdateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')
        self.other = User.objects.create_user(username='u2', password='pass12345')

    def test_requires_login(self):
        response = self.client.get(reverse('accounts:profile_edit'))
        self.assertEqual(response.status_code, 302)

    def test_updates_own_bio(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': '', 'last_name': '', 'bio': 'Xin chào',
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, 'Xin chào')

    def test_cannot_edit_another_users_profile(self):
        # get_object luôn trả về request.user, không nhận pk từ URL -> không có cách nào sửa hồ sơ người khác
        self.client.force_login(self.other)
        self.client.post(reverse('accounts:profile_edit'), {'first_name': '', 'last_name': '', 'bio': 'Hack'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, '')


class ActivityViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )

    def test_requires_login(self):
        response = self.client.get(reverse('accounts:activity'))
        self.assertEqual(response.status_code, 302)

    def test_lists_own_review(self):
        Review.objects.create(place=self.place, user=self.user, rating=5, content='Tốt')
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:activity'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['activity']), 1)


class UserWarningActionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345', email='u1@example.com')
        self.admin_user = User.objects.create_superuser(
            username='admin3', password='pass12345', email='admin3@example.com',
        )

    def test_send_warning_action_emails_user(self):
        model_admin = django_admin.site._registry[User]
        request = RequestFactory().get('/admin/')
        request.user = self.admin_user

        mail.outbox = []
        model_admin.send_warning(request, User.objects.filter(pk=self.user.pk))

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('u1@example.com', mail.outbox[0].to)
