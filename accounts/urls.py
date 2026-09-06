from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('activity/', views.activity_view, name='activity'),
    path('u/<str:username>/', views.ProfileDetailView.as_view(), name='profile_detail'),
]
