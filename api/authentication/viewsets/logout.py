from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from api.authentication.models import ActiveSession


class LogoutViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
	permission_classes = (IsAuthenticated,)

	def create(self, request, *args, **kwargs):
		user = request.user

		session_token = request.META.get("HTTP_AUTHORIZATION")

		if not session_token:
			return Response(
				{"error": "Session token not provided"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		# Find the session using the session token and the user
		try:
			session = ActiveSession.objects.get(user=user, token=session_token)
			session.delete()
			return Response(
				{"success": True, "msg": "Token revoked"}, status=status.HTTP_200_OK
			)
		except ActiveSession.DoesNotExist:
			return Response(
				{"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
			)
