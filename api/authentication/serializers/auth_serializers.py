
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from django.conf import settings
# from apps.authentication.models import CustomUser
from api.user.models import User
import json
from django.forms.models import model_to_dict
from django.core import serializers

class MySimpleJWTSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        user_obj = User.objects.get(username=user)
        # print("user_obj:", user_obj)  
        userData = serializers.serialize('json', [user_obj,])
        struct = json.loads(userData)
        userData = json.dumps(struct[0])
        # print("get_token_me:", userData)
        token["user"] = userData       
        return token

    def validate(self, attrs):
        credentials = {
            'username': '',
            'password': attrs.get("password")
        }
        # print("validate:", credentials) 
        user_obj = User.objects.filter(email=attrs.get("username")).first(
        ) or User.objects.filter(username=attrs.get("username")).first()
        if user_obj:
            credentials['username'] = user_obj.username
        return super().validate(credentials)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MySimpleJWTSerializer
