
from django.conf.urls import url, include
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from api.authentication.serializers.auth_serializers import MyTokenObtainPairView
from .viewsets.auth_views import *

secure_login = LoginByEmailLinkMVS.as_view({
    'get': 'secure_login'
})
delete_account = ManagerAccountMVS.as_view({
    'delete': 'delete_account'
})

urlpatterns = [
	path('facebook/', FacebookSocialLogin.as_view(), name='facebook-login'),
	path('google/', GoogleSocialLogin.as_view(), name='google-login'),
	path('linkedin/', LinkedInSocialLogin.as_view(), name='linkedin-login'),
	path('pinterest/', PinterestSocialLogin.as_view(), name='pinterest-login'),
	path('snapchat/', SnapchatSocialLogin.as_view(), name='snapchat-login'),
	path('tiktok/', TiktokSocialLogin.as_view(), name='tiktok-login'),

	# Sesame auth
    path('secure_login/<str:token_sesame>',
         secure_login),
    path('get_secure_login/', GetSecureLoginLink.as_view(), name='get_secure_login'),
    path('login-from-email-link/',
         GetSecureLoginLink.as_view(), name='login-from-email-link'),
    # 
	path('delete_account/', delete_account),
]
