from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from api.ad_accounts import views

urlpatterns = [
    path('', views.Add_Account.as_view(), name='ad-accounts'),
    path('notif/', views.ad_accounts_notif, name='ad-accounts-notif'),
]
