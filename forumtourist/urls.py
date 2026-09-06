from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('captcha/', include('captcha.urls')),
    path('', RedirectView.as_view(url='/places/', permanent=False)),
    path('', include('accounts.urls')),
    path('', include('places.urls')),
    path('', include('reviews.urls')),
    path('', include('lists.urls')),
    path('', include('forum.urls')),
    path('', include('moderation.urls')),
    path('', include('social.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
