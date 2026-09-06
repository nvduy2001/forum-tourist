from django.contrib.auth import get_user_model
from django.core import mail
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from places.models import Place
from reviews.models import Comment, Review

from .models import CommentLike, PlaceFollow, ReviewVote, UserFollow

User = get_user_model()


class UserFollowTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username='alice', password='pass12345', email='alice@example.com')
        self.bob = User.objects.create_user(username='bob', password='pass12345')

    def test_toggle_follow_creates_then_removes(self):
        self.client.force_login(self.bob)
        url = reverse('social:toggle_follow_user', args=[self.alice.username])

        mail.outbox = []
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['followed'])
        self.assertTrue(UserFollow.objects.filter(follower=self.bob, following=self.alice).exists())
        self.assertEqual(len(mail.outbox), 1)

        response = self.client.post(url)
        self.assertFalse(response.json()['followed'])
        self.assertFalse(UserFollow.objects.filter(follower=self.bob, following=self.alice).exists())

    def test_cannot_follow_self(self):
        self.client.force_login(self.alice)
        response = self.client.post(reverse('social:toggle_follow_user', args=[self.alice.username]))
        self.assertEqual(response.status_code, 400)

    def test_follow_self_blocked_at_db_level(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserFollow.objects.create(follower=self.alice, following=self.alice)


class PlaceFollowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )

    def test_toggle_follow_place(self):
        self.client.force_login(self.user)
        url = reverse('social:toggle_follow_place', args=[self.place.pk])

        response = self.client.post(url)
        self.assertTrue(response.json()['followed'])
        self.assertEqual(PlaceFollow.objects.filter(user=self.user, place=self.place).count(), 1)

        response = self.client.post(url)
        self.assertFalse(response.json()['followed'])

    def test_followers_notified_of_new_review(self):
        follower = User.objects.create_user(username='follower', password='pass12345', email='f@example.com')
        PlaceFollow.objects.create(user=follower, place=self.place)

        mail.outbox = []
        Review.objects.create(place=self.place, user=self.user, rating=5, content='Tốt')

        self.assertTrue(any('f@example.com' in m.to for m in mail.outbox))


class ReviewVoteTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='author', password='pass12345', email='author@example.com',
        )
        self.voter = User.objects.create_user(username='voter', password='pass12345')
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.review = Review.objects.create(place=self.place, user=self.author, rating=5, content='Tốt')

    def test_vote_awards_points_and_notifies(self):
        self.client.force_login(self.voter)
        mail.outbox = []

        response = self.client.post(reverse('social:toggle_review_vote', args=[self.review.pk]))
        self.assertTrue(response.json()['voted'])

        self.author.refresh_from_db()
        # +10 điểm khi tạo review (POINTS_PER_REVIEW) + 5 điểm khi được vote hữu ích
        self.assertEqual(self.author.points, 15)
        self.assertEqual(len(mail.outbox), 1)

    def test_unvote_does_not_remove_points(self):
        ReviewVote.objects.create(user=self.voter, review=self.review)
        self.client.force_login(self.voter)
        response = self.client.post(reverse('social:toggle_review_vote', args=[self.review.pk]))
        self.assertFalse(response.json()['voted'])


class CommentLikeTests(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name='Quán A', address='123 X', region='Hà Nội', category='food',
            latitude=21.0, longitude=105.8,
        )
        self.author = User.objects.create_user(username='author', password='pass12345')
        self.liker = User.objects.create_user(username='liker', password='pass12345')
        self.review = Review.objects.create(place=self.place, user=self.author, rating=5, content='Tốt')
        self.comment = Comment.objects.create(review=self.review, user=self.author, content='Bình luận')

    def test_toggle_comment_like(self):
        self.client.force_login(self.liker)
        url = reverse('social:toggle_comment_like', args=[self.comment.pk])

        response = self.client.post(url)
        self.assertTrue(response.json()['liked'])
        self.assertEqual(CommentLike.objects.filter(user=self.liker, comment=self.comment).count(), 1)

        response = self.client.post(url)
        self.assertFalse(response.json()['liked'])
