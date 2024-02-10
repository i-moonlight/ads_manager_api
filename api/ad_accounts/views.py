from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import AuthorizationSerializers
from datetime import datetime, timedelta
import traceback
from .models import *
from ..google_ads.utils.importer import import_google_ads_account_data 
from ..linkedin.utils.importer import import_linkedin_account_data  
from ..meta.utils.importer import import_meta_account_data 
from ..pinterest.utils.importer import import_pinterest_account_data
from ..snapchat.utils.importer import import_snapchat_account_data
from ..tiktok.utils.importer import import_tiktok_account_data
import os
from rest_framework_tracking.mixins import LoggingMixin
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django_q.tasks import async_task
from django_q.models import OrmQ
import requests
from rest_framework.decorators import api_view


def send_notif(task):
	requests.post(f'{os.environ.get("API_SERVER")}/api/ad_accounts/notif/', json=task.result)


class Add_Account(LoggingMixin, APIView):
	def post(self, request):
		print('Add_Account start')
		try:
			account_id = request.data.get("account_id")
			account_name = request.data.get("account_name")
			ad_platform = request.data.get("ad_platform")
			start_date = request.data.get('start_date', (datetime.now() - timedelta(days=365)))
			end_date = request.data.get('end_date', datetime.now())
			current_user = request.user
			Authorizations.objects.filter(user=current_user, account_id=None, ad_platform=ad_platform).update(account_id=account_id, account_name=account_name, date_time=datetime.utcnow(), )

			authorized_platforms_list = list(Authorizations.objects.filter(
				user=current_user).exclude(account_id__isnull=True).all())
			context = {}
			authorized_platforms = {}
			for i in authorized_platforms_list:
				authorized_platforms[i.ad_platform] = i.account_name

				context['authorized_platforms'] = authorized_platforms
				context['segment'] = 'ad-accounts'
				context['title'] = 'Connected ad accounts'

			serializer = AuthorizationSerializers(Authorizations.objects.get(user=current_user, ad_platform=ad_platform))

			if ad_platform == 'google_ads':
				async_task(import_google_ads_account_data, account_id, current_user, hook=send_notif)
			elif ad_platform == 'linkedin':
				async_task(import_linkedin_account_data, account_id, current_user, hook=send_notif)
			elif ad_platform == 'meta_ads':
				async_task(import_meta_account_data, account_id, current_user, hook=send_notif)
			elif ad_platform == 'pinterest':
				async_task(import_pinterest_account_data, account_id, current_user, hook=send_notif)
			elif ad_platform == 'snapchat':
				async_task(import_snapchat_account_data, account_id, current_user, hook=send_notif)
			elif ad_platform == 'tiktok':
				async_task(import_tiktok_account_data, account_id, current_user, start_date, end_date, hook=send_notif)

			task_id = OrmQ.objects.last().id

			channel_layer = get_channel_layer()

			async_to_sync(channel_layer.group_send)('ad-accounts', {
				'type': 'send_notification',
				'ad_platform': ad_platform,
				'is_importing': True,
				'task_id': task_id
			})

			return Response({"message": 'success', **serializer.data})
		except Exception as e:
			print('Add_Account Error')
			print(e)
			traceback.print_exc()  # Print the traceback information
			return Response({"message": 'false'})
	
	def get(self,request,format=None):
		account_ads = Authorizations.objects.filter(user=request.user)
		if account_ads:
			serializer = AuthorizationSerializers(account_ads,many=True)
			return Response({"message": 'success', 'accounts': serializer.data,"ads":True})
		else:
			return Response({"message": 'false', 'accounts': [], "ads":False})


@api_view(['POST'])
def ad_accounts_notif(request):
	channel_layer = get_channel_layer()

	async_to_sync(channel_layer.group_send)('ad-accounts', {
		'type': 'send_notification',
		'message': request.data.get('message'),
		'ad_platform': request.data.get('ad_platform'),
		'is_importing': request.data.get('is_importing')
	})

	return Response(status=200)