from django.urls import path

from . import views

app_name = 'lists'

urlpatterns = [
    path('lists/', views.ListListView.as_view(), name='list_list'),
    path('lists/new/', views.ListCreateView.as_view(), name='list_create'),
    path('lists/<int:pk>/', views.ListDetailView.as_view(), name='list_detail'),
    path('lists/<int:pk>/edit/', views.ListUpdateView.as_view(), name='list_update'),
    path('lists/<int:pk>/delete/', views.ListDeleteView.as_view(), name='list_delete'),
    path('lists/<int:list_id>/items/<int:place_id>/add/', views.add_place_to_list, name='add_place'),
    path('lists/<int:list_id>/items/<int:place_id>/remove/', views.remove_place_from_list, name='remove_place'),
]
