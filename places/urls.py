from django.urls import path

from . import views

app_name = 'places'

urlpatterns = [
    path('places/', views.PlaceListView.as_view(), name='place_list'),
    path('places/new/', views.PlaceCreateView.as_view(), name='place_create'),
    path('places/<int:pk>/', views.PlaceDetailView.as_view(), name='place_detail'),
    path('places/<int:pk>/edit/', views.PlaceUpdateView.as_view(), name='place_update'),
    path('places/<int:place_id>/claim-ownership/', views.request_ownership, name='request_ownership'),
    path('places/<int:place_id>/images/add/', views.add_place_image, name='add_place_image'),
    path('places/<int:place_id>/images/<int:image_id>/delete/', views.delete_place_image, name='delete_place_image'),
    path('places/<int:place_id>/menu/add/', views.add_menu_item, name='add_menu_item'),
    path('places/<int:place_id>/menu/<int:item_id>/delete/', views.delete_menu_item, name='delete_menu_item'),
    path('places/<int:place_id>/promotions/new/', views.create_promotion, name='create_promotion'),
]
