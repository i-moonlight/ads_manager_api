from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import ContactSerializer
from django.core.mail import send_mail
from django.conf import settings

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def contact(request):
  if (request.method == 'POST'):
    
     # Get the client's IP address
    ipaddress = get_client_ip(request)

   # Include the IP address in the data
    data = request.data.copy()
    data['ip_address'] = ipaddress

    serializer = ContactSerializer(data=data)

    serializer.is_valid(raise_exception=True)

    serializer.save()

    email = serializer.data.get('email')
   
    send_mail(
      f'Message from {email}',
      serializer.data.get('comment'),
      settings.EMAIL_HOST_USER,
      [settings.SEND_CONTACT_TO],
      fail_silently=False
    )

    return Response(serializer.data)

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
