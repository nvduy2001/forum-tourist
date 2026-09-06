from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django_ratelimit.decorators import ratelimit

from .models import ForumPost


class ForumPostListView(ListView):
    model = ForumPost
    context_object_name = 'posts'

    def get_queryset(self):
        queryset = ForumPost.objects.all()
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset


class ForumPostDetailView(DetailView):
    model = ForumPost
    context_object_name = 'post'


@method_decorator(ratelimit(key='user', rate='5/m', block=True), name='post')
class ForumPostCreateView(LoginRequiredMixin, CreateView):
    model = ForumPost
    fields = ['category', 'title', 'content']

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ForumPostAuthorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.get_object().user_id == self.request.user.id


class ForumPostUpdateView(ForumPostAuthorRequiredMixin, UpdateView):
    model = ForumPost
    fields = ['category', 'title', 'content']


class ForumPostDeleteView(ForumPostAuthorRequiredMixin, DeleteView):
    model = ForumPost
    success_url = '/forum/'
