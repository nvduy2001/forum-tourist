from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.test import RequestFactory, TestCase
from django.urls import reverse

from places.models import Place

from .models import Report

User = get_user_model()


class CreateReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reporter', password='pass12345')
        self.place = Place.objects.create(
            name='Quán A', address='123 Đường X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )

    def test_requires_login(self):
        response = self.client.post(reverse('moderation:create_report'), {
            'app_label': 'places', 'model': 'place', 'object_id': self.place.id, 'reason': 'spam',
        })
        self.assertEqual(response.status_code, 302)

    def test_creates_report_against_place(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('moderation:create_report'), {
            'app_label': 'places', 'model': 'place', 'object_id': self.place.id, 'reason': 'Thông tin sai',
        })
        self.assertEqual(response.status_code, 200)

        report = Report.objects.get(pk=response.json()['report_id'])
        self.assertEqual(report.reporter, self.user)
        self.assertEqual(report.content_object, self.place)
        self.assertEqual(report.status, Report.Status.PENDING)

    def test_missing_reason_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('moderation:create_report'), {
            'app_label': 'places', 'model': 'place', 'object_id': self.place.id,
        })
        self.assertEqual(response.status_code, 400)


class ReportResolutionNotificationTests(TestCase):
    def setUp(self):
        self.reporter = User.objects.create_user(
            username='reporter', password='pass12345', email='reporter@example.com',
        )
        self.admin_user = User.objects.create_superuser(
            username='admin2', password='pass12345', email='admin2@example.com',
        )
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.report = Report.objects.create(
            reporter=self.reporter,
            content_type=ContentType.objects.get_for_model(Place),
            object_id=self.place.id,
            reason='Spam',
        )

    def _admin_request(self):
        request = RequestFactory().get('/admin/')
        request.user = self.admin_user
        return request

    def test_resolving_report_notifies_reporter(self):
        model_admin = django_admin.site._registry[Report]
        mail.outbox = []
        model_admin.mark_resolved(self._admin_request(), Report.objects.filter(pk=self.report.pk))

        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Report.Status.RESOLVED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reporter@example.com', mail.outbox[0].to)
