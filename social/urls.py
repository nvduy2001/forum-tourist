from django.urls import path

from . import views

app_name = 'social'

urlpatterns = [
    path('users/<str:username>/follow/', views.toggle_follow_user, name='toggle_follow_user'),
    path('places/<int:place_id>/follow/', views.toggle_follow_place, name='toggle_follow_place'),
    path('reviews/<int:review_id>/vote/', views.toggle_review_vote, name='toggle_review_vote'),
    path('comments/<int:comment_id>/like/', views.toggle_comment_like, name='toggle_comment_like'),
]
