from django.urls import path
from api.snapchat import views

urlpatterns = [

    path('enable',views.Enable.as_view(),name='enable'),
   	path('disable', views.DisableAPI.as_view(), name='disable'),
	path('oauth',views.Oauth.as_view(),name='oauth'),
]
