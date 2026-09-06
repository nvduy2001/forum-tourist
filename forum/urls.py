from django.urls import path

from . import views

app_name = 'forum'

urlpatterns = [
    path('forum/', views.ForumPostListView.as_view(), name='post_list'),
    path('forum/new/', views.ForumPostCreateView.as_view(), name='post_create'),
    path('forum/<int:pk>/', views.ForumPostDetailView.as_view(), name='post_detail'),
    path('forum/<int:pk>/edit/', views.ForumPostUpdateView.as_view(), name='post_update'),
    path('forum/<int:pk>/delete/', views.ForumPostDeleteView.as_view(), name='post_delete'),
]
