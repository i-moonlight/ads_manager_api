from django.urls import path
from api.meta import views

urlpatterns = [

    path('enable',views.Enable.as_view(),name='enable'),
   	path('disable', views.DisableAPI.as_view(), name='disable'),
	path('oauth',views.Oauth.as_view(),name='oauth'),
	path('pages',views.Pages.as_view(),name='pages'),
	path('accounts',views.Accounts.as_view(),name='accounts'),
]
