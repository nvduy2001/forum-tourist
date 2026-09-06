import io
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from gamification.models import Badge, MissionProgress, SeasonalMission, UserBadge
from places.models import Place

from .models import Comment, Review, ReviewMedia, ReviewTag
from .signals import DISCOVERER_BADGE_SLUG
from .utils import haversine_distance_m

User = get_user_model()


class HaversineDistanceTests(TestCase):
    def test_same_point_is_zero_distance(self):
        self.assertAlmostEqual(haversine_distance_m(10.0, 106.0, 10.0, 106.0), 0.0, places=3)

    def test_known_distance_hanoi_to_hcmc(self):
        # Hà Nội (21.0278, 105.8342) -> TP.HCM (10.7769, 106.7009), thực tế ~1140-1160km
        distance_m = haversine_distance_m(21.0278, 105.8342, 10.7769, 106.7009)
        self.assertGreater(distance_m, 1_100_000)
        self.assertLess(distance_m, 1_200_000)

    def test_small_offset_within_checkin_threshold(self):
        # ~0.002 độ vĩ độ lệch ~ 222m, dùng để kiểm tra ngưỡng check-in 200-300m
        distance_m = haversine_distance_m(10.0000, 106.0000, 10.0020, 106.0000)
        self.assertGreater(distance_m, 200)
        self.assertLess(distance_m, 260)


class ReviewCountAndDiscovererBadgeTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name='Quán A', address='123 Đường X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.user1 = User.objects.create_user(username='u1', password='pass12345')
        self.user2 = User.objects.create_user(username='u2', password='pass12345')

    def test_review_count_increments_on_create(self):
        Review.objects.create(place=self.place, user=self.user1, rating=5, content='Tốt')
        self.place.refresh_from_db()
        self.assertEqual(self.place.review_count, 1)

        Review.objects.create(place=self.place, user=self.user2, rating=4, content='Ổn')
        self.place.refresh_from_db()
        self.assertEqual(self.place.review_count, 2)

    def test_review_count_decrements_on_delete(self):
        review = Review.objects.create(place=self.place, user=self.user1, rating=5, content='Tốt')
        self.place.refresh_from_db()
        self.assertEqual(self.place.review_count, 1)

        review.delete()
        self.place.refresh_from_db()
        self.assertEqual(self.place.review_count, 0)

    def test_first_review_awards_discoverer_badge(self):
        Review.objects.create(place=self.place, user=self.user1, rating=5, content='Đầu tiên')

        badge = Badge.objects.get(slug=DISCOVERER_BADGE_SLUG)
        self.assertTrue(UserBadge.objects.filter(user=self.user1, badge=badge).exists())

    def test_second_review_does_not_award_discoverer_badge(self):
        Review.objects.create(place=self.place, user=self.user1, rating=5, content='Đầu tiên')
        Review.objects.create(place=self.place, user=self.user2, rating=3, content='Sau')

        badge = Badge.objects.get(slug=DISCOVERER_BADGE_SLUG)
        self.assertFalse(UserBadge.objects.filter(user=self.user2, badge=badge).exists())
        self.assertEqual(UserBadge.objects.filter(badge=badge).count(), 1)

    def test_first_review_sends_badge_notification_email(self):
        self.user1.email = 'u1@example.com'
        self.user1.save(update_fields=['email'])

        mail.outbox = []
        Review.objects.create(place=self.place, user=self.user1, rating=5, content='Đầu tiên')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('u1@example.com', mail.outbox[0].to)


class CommentNotificationTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.author = User.objects.create_user(
            username='author', password='pass12345', email='author@example.com',
        )
        self.commenter = User.objects.create_user(username='commenter', password='pass12345')
        self.review = Review.objects.create(place=self.place, user=self.author, rating=5, content='Tốt')

    def test_comment_by_other_user_notifies_review_author(self):
        mail.outbox = []
        Comment.objects.create(review=self.review, user=self.commenter, content='Đồng ý!')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('author@example.com', mail.outbox[0].to)

    def test_self_comment_does_not_notify(self):
        mail.outbox = []
        Comment.objects.create(review=self.review, user=self.author, content='Bổ sung thêm')

        self.assertEqual(len(mail.outbox), 0)


class SeasonalMissionProgressTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')
        self.badge = Badge.objects.create(name='Đại sứ mùa hè', slug='dai-su-mua-he')
        today = timezone.localdate()
        self.mission = SeasonalMission.objects.create(
            name='Đại sứ Hà Nội mùa hè',
            region='Hà Nội',
            category='food',
            required_count=2,
            badge=self.badge,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=30),
        )
        self.place = Place.objects.create(
            name='Quán A', address='123 Đường X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )

    def test_matching_review_increments_progress(self):
        Review.objects.create(place=self.place, user=self.user, rating=5, content='1')

        progress = MissionProgress.objects.get(mission=self.mission, user=self.user)
        self.assertEqual(progress.progress_count, 1)
        self.assertIsNone(progress.completed_at)

    def test_reaching_required_count_awards_badge_and_completes(self):
        Review.objects.create(place=self.place, user=self.user, rating=5, content='1')
        Review.objects.create(place=self.place, user=self.user, rating=4, content='2')

        progress = MissionProgress.objects.get(mission=self.mission, user=self.user)
        self.assertEqual(progress.progress_count, 2)
        self.assertIsNotNone(progress.completed_at)
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge=self.badge).exists())

    def test_review_outside_region_does_not_affect_progress(self):
        other_place = Place.objects.create(
            name='Quán B', address='456 Đường Y', region='Đà Nẵng', category='food',
            latitude=16.0, longitude=108.2,
        )
        Review.objects.create(place=other_place, user=self.user, rating=5, content='Ngoài phạm vi')

        self.assertFalse(MissionProgress.objects.filter(mission=self.mission, user=self.user).exists())

    def test_review_outside_date_range_does_not_affect_progress(self):
        self.mission.start_date = timezone.localdate() + timedelta(days=5)
        self.mission.save(update_fields=['start_date'])

        Review.objects.create(place=self.place, user=self.user, rating=5, content='Chưa tới mùa')

        self.assertFalse(MissionProgress.objects.filter(mission=self.mission, user=self.user).exists())

    def test_progress_does_not_exceed_required_after_completion(self):
        Review.objects.create(place=self.place, user=self.user, rating=5, content='1')
        Review.objects.create(place=self.place, user=self.user, rating=4, content='2')
        Review.objects.create(place=self.place, user=self.user, rating=3, content='3')

        progress = MissionProgress.objects.get(mission=self.mission, user=self.user)
        self.assertEqual(progress.progress_count, 2)
        self.assertEqual(UserBadge.objects.filter(user=self.user, badge=self.badge).count(), 1)


class ReviewEditWindowTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.author = User.objects.create_user(username='author', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')
        self.review = Review.objects.create(place=self.place, user=self.author, rating=4, content='Ổn')

    def test_review_is_editable_right_after_creation(self):
        self.assertTrue(self.review.is_editable)

    def test_review_not_editable_after_24h(self):
        Review.objects.filter(pk=self.review.pk).update(created_at=timezone.now() - timedelta(hours=25))
        self.review.refresh_from_db()
        self.assertFalse(self.review.is_editable)

    def test_author_can_update_within_window(self):
        self.client.force_login(self.author)
        response = self.client.post(reverse('reviews:review_update', args=[self.review.pk]), {
            'rating': 5, 'content': 'Cập nhật',
        })
        self.assertEqual(response.status_code, 302)
        self.review.refresh_from_db()
        self.assertEqual(self.review.content, 'Cập nhật')

    def test_other_user_cannot_update(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse('reviews:review_update', args=[self.review.pk]))
        self.assertEqual(response.status_code, 403)

    def test_author_cannot_update_after_24h(self):
        Review.objects.filter(pk=self.review.pk).update(created_at=timezone.now() - timedelta(hours=25))
        self.client.force_login(self.author)
        response = self.client.get(reverse('reviews:review_update', args=[self.review.pk]))
        self.assertEqual(response.status_code, 403)

    def test_author_can_delete_within_window(self):
        self.client.force_login(self.author)
        response = self.client.post(reverse('reviews:review_delete', args=[self.review.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(pk=self.review.pk).exists())


class ThreadedCommentTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.author = User.objects.create_user(username='author', password='pass12345')
        self.replier = User.objects.create_user(username='replier', password='pass12345')
        self.review = Review.objects.create(place=self.place, user=self.author, rating=4, content='Ổn')

    def test_reply_to_comment_sets_parent(self):
        self.client.force_login(self.author)
        top = Comment.objects.create(review=self.review, user=self.author, content='Bình luận gốc')

        self.client.force_login(self.replier)
        response = self.client.post(reverse('reviews:add_comment', args=[self.review.pk]), {
            'content': 'Trả lời', 'parent_id': top.pk,
        })
        self.assertEqual(response.status_code, 200)

        reply = Comment.objects.get(content='Trả lời')
        self.assertEqual(reply.parent_id, top.pk)
        self.assertEqual(list(top.replies.all()), [reply])


class ReviewSubmissionExtrasTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.user = User.objects.create_user(username='u1', password='pass12345')
        self.tag = ReviewTag.objects.create(name='Yên tĩnh', slug='yen-tinh')

    def test_write_review_saves_sub_ratings_and_tags(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('reviews:write_review', args=[self.place.pk]), {
            'rating': 5, 'quality_rating': 4, 'price_rating': 3, 'content': 'Tốt', 'tags': [self.tag.pk],
        })
        self.assertEqual(response.status_code, 200)

        review = Review.objects.get(place=self.place, user=self.user)
        self.assertEqual(review.quality_rating, 4)
        self.assertEqual(review.price_rating, 3)
        self.assertIn(self.tag, review.tags.all())

    def test_write_review_saves_media_attachment(self):
        self.client.force_login(self.user)
        image = io.BytesIO(b'fake-image-bytes')
        image.name = 'photo.jpg'

        response = self.client.post(reverse('reviews:write_review', args=[self.place.pk]), {
            'rating': 5, 'content': 'Có ảnh', 'media': image,
        })
        self.assertEqual(response.status_code, 200)

        review = Review.objects.get(place=self.place, user=self.user)
        self.assertEqual(review.media.count(), 1)
        self.assertEqual(review.media.first().media_type, ReviewMedia.MediaType.IMAGE)


class ReviewHiddenFromPublicViewTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.author = User.objects.create_user(username='author', password='pass12345')
        self.staff = User.objects.create_user(username='staff', password='pass12345', is_staff=True)
        self.review = Review.objects.create(
            place=self.place, user=self.author, rating=5, content='Nội dung vi phạm',
        )

    def test_hidden_review_not_shown_to_anonymous(self):
        self.review.is_hidden = True
        self.review.save(update_fields=['is_hidden'])

        response = self.client.get(reverse('places:place_detail', args=[self.place.pk]))
        self.assertNotIn(self.review, list(response.context['reviews']))

    def test_hidden_review_still_visible_to_staff(self):
        self.review.is_hidden = True
        self.review.save(update_fields=['is_hidden'])

        self.client.force_login(self.staff)
        response = self.client.get(reverse('places:place_detail', args=[self.place.pk]))
        self.assertIn(self.review, list(response.context['reviews']))

    def test_admin_hide_and_restore_actions(self):
        from django.contrib import admin as django_admin
        from django.test import RequestFactory

        model_admin = django_admin.site._registry[Review]
        request = RequestFactory().get('/admin/')
        request.user = self.staff

        model_admin.hide_reviews(request, Review.objects.filter(pk=self.review.pk))
        self.review.refresh_from_db()
        self.assertTrue(self.review.is_hidden)

        model_admin.restore_reviews(request, Review.objects.filter(pk=self.review.pk))
        self.review.refresh_from_db()
        self.assertFalse(self.review.is_hidden)
