
from django.conf.urls import url, include
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from api.authentication.serializers.auth_serializers import MyTokenObtainPairView
from .views import *

get_all_image_by_user_api = MediaMVS.as_view({
    'get': 'get_all_image_by_user_api'
})
delete_image_by_user_api = MediaMVS.as_view({
    'delete': 'delete_image_by_user_api'
})

upload_image_api = UploadImageLibraryMVS.as_view({
    'post': 'upload_image_api'
})

urlpatterns = [
   path('get_all_image_by_user_api/', get_all_image_by_user_api),  
   path('delete_image_by_user_api/', delete_image_by_user_api), 
   path('upload_image_api/', upload_image_api),  
]
