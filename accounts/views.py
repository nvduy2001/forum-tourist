import itertools

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, UpdateView

from forum.models import ForumPost
from gamification.models import UserBadge
from lists.models import List
from reviews.models import Comment, Review
from social.models import PlaceFollow, UserFollow

from .forms import ProfileForm

User = get_user_model()


class ProfileDetailView(DetailView):
    model = User
    context_object_name = 'profile_user'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    template_name = 'accounts/profile_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.object
        context['review_count'] = profile_user.reviews.count()
        context['badges'] = UserBadge.objects.filter(user=profile_user).select_related('badge')
        context['follower_count'] = profile_user.followers.count()
        context['following_count'] = profile_user.following.count()
        context['public_lists'] = List.objects.filter(user=profile_user, is_public=True)

        if self.request.user.is_authenticated and self.request.user != profile_user:
            context['is_following'] = UserFollow.objects.filter(
                follower=self.request.user, following=profile_user
            ).exists()

        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = 'accounts/profile_form.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        from django.urls import reverse

        return reverse('accounts:profile_detail', args=[self.request.user.username])


@login_required
def activity_view(request):
    """Lịch sử hoạt động của bản thân: review, bình luận, bài diễn đàn đã đăng."""
    reviews = Review.objects.filter(user=request.user).select_related('place')
    comments = Comment.objects.filter(user=request.user).select_related('review__place')
    posts = ForumPost.objects.filter(user=request.user)
    followed_places = PlaceFollow.objects.filter(user=request.user).select_related('place')

    activity = sorted(
        itertools.chain(
            ({'type': 'review', 'obj': r, 'created_at': r.created_at} for r in reviews),
            ({'type': 'comment', 'obj': c, 'created_at': c.created_at} for c in comments),
            ({'type': 'post', 'obj': p, 'created_at': p.created_at} for p in posts),
        ),
        key=lambda item: item['created_at'],
        reverse=True,
    )

    return render(request, 'accounts/activity.html', {
        'activity': activity,
        'followed_places': followed_places,
    })
