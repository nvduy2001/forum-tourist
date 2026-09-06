from django.urls import path

from . import views

app_name = 'moderation'

urlpatterns = [
    path('reports/new/', views.create_report, name='create_report'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
