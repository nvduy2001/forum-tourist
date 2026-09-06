from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from places.models import Place
from reviews.models import Comment, Review

from .models import Badge, UserBadge
from .services import add_points, get_member_tier
from .tasks import award_monthly_badges

User = get_user_model()


class PointsAndTierTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )

    def test_add_points_accumulates(self):
        add_points(self.user, 10)
        add_points(self.user, 5)
        self.user.refresh_from_db()
        self.assertEqual(self.user.points, 15)

    def test_writing_review_awards_points(self):
        Review.objects.create(place=self.place, user=self.user, rating=5, content='Tốt')
        self.user.refresh_from_db()
        self.assertEqual(self.user.points, 10)

    def test_writing_comment_awards_points(self):
        review = Review.objects.create(place=self.place, user=self.user, rating=5, content='Tốt')
        Comment.objects.create(review=review, user=self.user, content='Bình luận')
        self.user.refresh_from_db()
        self.assertEqual(self.user.points, 10 + 2)

    def test_member_tier_thresholds(self):
        self.assertEqual(get_member_tier(0), 'Người mới')
        self.assertEqual(get_member_tier(99), 'Người mới')
        self.assertEqual(get_member_tier(100), 'Reviewer')
        self.assertEqual(get_member_tier(499), 'Reviewer')
        self.assertEqual(get_member_tier(500), 'Chuyên gia địa phương')

    def test_user_member_tier_property(self):
        add_points(self.user, 150)
        self.assertEqual(self.user.member_tier, 'Reviewer')


class MonthlyBadgeTaskTests(TestCase):
    def setUp(self):
        self.top_reviewer = User.objects.create_user(username='top', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')
        self.food_place = Place.objects.create(
            name='Quán ăn', address='1 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.hotel_place = Place.objects.create(
            name='Khách sạn', address='2 X', region='Hà Nội', category='hotel',
            latitude=21.0, longitude=105.8,
        )

        last_month = timezone.now().replace(day=1) - timedelta(days=1)
        for i in range(3):
            review = Review.objects.create(
                place=self.food_place, user=self.top_reviewer, rating=5, content=f'R{i}',
            )
            Review.objects.filter(pk=review.pk).update(created_at=last_month)
        review = Review.objects.create(place=self.hotel_place, user=self.other, rating=4, content='R')
        Review.objects.filter(pk=review.pk).update(created_at=last_month)

    def test_awards_reviewer_of_month_and_food_expert(self):
        award_monthly_badges()

        self.assertTrue(
            UserBadge.objects.filter(user=self.top_reviewer, badge__slug__startswith='nguoi-danh-gia-thang-').exists()
        )
        self.assertTrue(
            UserBadge.objects.filter(user=self.top_reviewer, badge__slug__startswith='chuyen-gia-am-thuc-').exists()
        )
        self.assertFalse(
            UserBadge.objects.filter(user=self.other, badge__slug__startswith='chuyen-gia-am-thuc-').exists()
        )

    def test_running_twice_does_not_duplicate_badge(self):
        award_monthly_badges()
        award_monthly_badges()

        badge = Badge.objects.get(slug__startswith='nguoi-danh-gia-thang-')
        self.assertEqual(UserBadge.objects.filter(user=self.top_reviewer, badge=badge).count(), 1)
