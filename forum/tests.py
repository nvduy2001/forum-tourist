from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import ForumPost

User = get_user_model()


class ForumPostCategoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')
        ForumPost.objects.create(
            user=self.user, category=ForumPost.Category.TRAVEL_EXPERIENCE, title='Kinh nghiệm', content='...',
        )
        ForumPost.objects.create(
            user=self.user, category=ForumPost.Category.SERVICE_QA, title='Hỏi đáp', content='...',
        )

    def test_filter_by_category(self):
        response = self.client.get(reverse('forum:post_list'), {'category': 'kinh_nghiem_du_lich'})
        self.assertEqual(list(response.context['posts']), list(
            ForumPost.objects.filter(category='kinh_nghiem_du_lich')
        ))

    def test_no_filter_returns_all(self):
        response = self.client.get(reverse('forum:post_list'))
        self.assertEqual(response.context['posts'].count(), 2)


class ForumPostCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')

    def test_create_post_requires_login(self):
        response = self.client.get(reverse('forum:post_create'))
        self.assertEqual(response.status_code, 302)

    def test_create_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('forum:post_create'), {
            'category': 'khac', 'title': 'Bài mới', 'content': 'Nội dung',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ForumPost.objects.filter(title='Bài mới', user=self.user).exists())
