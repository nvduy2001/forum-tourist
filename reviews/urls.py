from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('places/<int:place_id>/write-review/', views.write_review_page, name='write_review_page'),
    path('places/<int:place_id>/reviews/', views.write_review, name='write_review'),
    path('places/<int:place_id>/check-in/', views.check_in, name='check_in'),
    path('reviews/<int:pk>/edit/', views.ReviewUpdateView.as_view(), name='review_update'),
    path('reviews/<int:pk>/delete/', views.ReviewDeleteView.as_view(), name='review_delete'),
    path('reviews/<int:review_id>/comments/', views.add_comment, name='add_comment'),
    path('reviews/<int:review_id>/owner-reply/', views.reply_as_owner, name='reply_as_owner'),
]
