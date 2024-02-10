import jwt
from rest_framework import serializers, exceptions
from django.contrib.auth import authenticate
from datetime import datetime, timedelta
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from api.authentication.models import ActiveSession

def _get_user_id_from_token(request):
	try:
		jwtDecode = jwt.decode(request.META['HTTP_AUTHORIZATION'], settings.SECRET_KEY, algorithms=["HS256"])
		return jwtDecode['id']   
	except jwt.DecodeError as exc:
		print("_get_user_id_from_token: ", str(exc))
		return 0

def _generate_jwt_token(user):
	token = jwt.encode(
		{"id": user.pk, "exp": datetime.utcnow() + timedelta(days=7)},
		settings.SECRET_KEY,
	)

	return token


class LoginSerializer(serializers.Serializer):
	email = serializers.CharField(max_length=255)
	username = serializers.CharField(max_length=255, read_only=True)
	password = serializers.CharField(max_length=128, write_only=True)

	def validate(self, data):
		email = data.get("email", None)
		password = data.get("password", None)

		if email is None:
			raise exceptions.ValidationError(
				{"success": False, "msg": "Email is required to login"}
			)
		if password is None:
			raise exceptions.ValidationError(
				{"success": False, "msg": "Password is required to log in."}
			)
		user = authenticate(email=email, password=password)

		if user is None:
			raise exceptions.AuthenticationFailed({"success": False, "msg": "Wrong credentials"})

		if not user.is_active:
			raise exceptions.ValidationError(
				{"success": False, "msg": "User is not active"}
			)

		try:
			session = ActiveSession.objects.get(user=user)
			if not session.token:
				raise ValueError

			jwt.decode(session.token, settings.SECRET_KEY, algorithms=["HS256"])

		except (ObjectDoesNotExist, ValueError, jwt.ExpiredSignatureError):
			session = ActiveSession.objects.create(
				user=user, token=_generate_jwt_token(user)
			)

		return {
			"success": True,
			"token": session.token,
			"user": {"_id": user.pk, "username": user.username, "display_name": user.username, "email": user.email, "created": user.date},
		}
		


