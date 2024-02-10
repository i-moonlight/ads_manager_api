from django.urls import path, include
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings

from api.ad_accounts.consumers import AdAccountsConsumer

admin.autodiscover()

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/users/", include(("api.routers", "api"), namespace="api")),
	path('api/auth/', include('api.authentication.urls')),
	path('api/contact/', include('api.contact.urls')),
    # 
    path('api/media_library/', include('api.media_library.urls')),
	path("api/google_ads/", include("api.google_ads.urls")),
	path("api/linkedin/", include("api.linkedin.urls")),
    path("api/meta_ads/", include("api.meta.urls")),
	path("api/pinterest/", include("api.pinterest.urls")),
	path("api/snapchat/", include("api.snapchat.urls")),
	path("api/tiktok/", include("api.tiktok.urls")),
    path("api/ad_accounts/", include("api.ad_accounts.urls")),
	path("api/ad_manager/", include('api.ad_manager.urls')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

websocket_urlpatterns = [
	path('ws/ad-accounts/', AdAccountsConsumer.as_asgi()),
	path('ws/ad-manager/', AdAccountsConsumer.as_asgi())
]