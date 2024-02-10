from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin
import requests

from ..ad_accounts.models import Authorizations
from .models import *
from datetime import datetime, timedelta
import uuid
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django_q.models import OrmQ

client_id = getattr(settings, 'LINKEDIN_OAUTH_CLIENT_ID')
client_secret = getattr(settings, 'LINKEDIN_OAUTH_CLIENT_SECRET')
linkedin_api_version = getattr(settings, 'LINKEDIN_API_VERSION')

class Enable(LoggingMixin, APIView):
	def get(self, request):
		print('ENABLE LINKEDIN')
		Authorizations.objects.filter(
			user=request.user, ad_platform='linkedin').delete()
		
		auth_url = 'https://www.linkedin.com/oauth/v2/authorization'    
		redirect_uri = getattr(settings, 'FE_SERVER') + '/ad-accounts'
		state = uuid.uuid4()
		state = str(state)

		params = {
					"response_type": "code",
					"client_id": client_id,
					"redirect_uri": redirect_uri,
					"status": "ACTIVE",
					"state": state,
					"scope": "rw_ads r_ads_reporting r_organization_social w_organization_social"
					}

		accesscode = requests.get(auth_url , params=params)
		authorization_url = accesscode.url

		return Response({"authorization_url": authorization_url})


class DisableAPI(LoggingMixin, APIView):
	def delete(self, request):
		print('disabled linkedin')
		ad_platform = 'linkedin'
		task_id = request.data.get('taskId')

		Authorizations.objects.filter(
			user=request.user, ad_platform=ad_platform).delete()

		Campaigns.objects.filter(
			user=request.user, 
			campaigns_platform__ad_platform=ad_platform, 
			campaigns_platform__api_id__isnull=False 
		).update(is_deleted=True)

		AdSets.objects.filter(
			user=request.user, 
			ad_sets_platform__ad_platform=ad_platform, 
			ad_sets_platform__api_id__isnull=False
		).update(is_deleted=True)

		Ads.objects.filter(
			user=request.user,
			ads_platform__ad_platform=ad_platform,
			ads_platform__api_id__isnull=False
		).update(is_deleted=True)


		if task_id:
			try:
				ormq = OrmQ.objects.get(id=task_id)
				ormq.delete()

				channel_layer = get_channel_layer()
				async_to_sync(channel_layer.group_send)('ad-accounts', {
					'type': 'send_notification',
					'ad_platform': ad_platform,
					'is_importing': False,
					'message': 'Import cancelled'
				})
			except OrmQ.DoesNotExist:
				pass

		return Response(status=status.HTTP_204_NO_CONTENT)


class Oauth(LoggingMixin, APIView):
	def post(self, request):
		code = request.data.get("code")
		code = str(code)

		# Get Access token
		print('linkedin oauth')
		redirect_uri = getattr(settings, 'FE_SERVER') + '/ad-accounts'

		access_token_url = 'https://www.linkedin.com/oauth/v2/accessToken'

		payload = {
			'grant_type' : 'authorization_code',
			'code' : code,
			'client_id' : client_id,
			'client_secret' : client_secret,
			'redirect_uri' : redirect_uri,
		}

		token_info = requests.post(url=access_token_url, params=payload)
		token_info = token_info.json()

		access_token = token_info['access_token']
		expires_in = token_info['expires_in']
		access_token_expiry = datetime.utcnow() + timedelta(seconds=expires_in) 
		refresh_token = token_info['refresh_token']


		authorization = Authorizations()
		authorization.user = request.user
		authorization.ad_platform = 'linkedin'
		authorization.refresh_token = refresh_token
		authorization.access_token = access_token
		authorization.access_token_expiry = access_token_expiry
		authorization.save()

		ad_account_details_url = 'https://api.linkedin.com/rest/adAccounts?q=search&search=(type:(values:List(BUSINESS)),status:(values:List(ACTIVE,CANCELED)))&sort=(field:ID,order:DESCENDING)'
	
		bearer_token = "Bearer " + str(access_token)
		
		headers = {
			'X-Restli-Protocol-Version': '2.0.0',
			'Linkedin-Version': linkedin_api_version,
			"Authorization": bearer_token,
		}

		response = requests.get(url=ad_account_details_url, headers=headers)
		
		account_details  = response.json()
		print(account_details)
		account_ids =  account_details['elements']
		

		if len(account_ids) == 1:
		
			account_id = account_ids[0]['id']
			account_name = account_ids[0]['name']
			authorization.account_id = account_id
			authorization.account_name = account_name
			authorization.date_time = datetime.utcnow()
			authorization.save()

			return Response({'accounts': account_name, 'ad_platform': 'meta_ads'})
		else:
			accounts = []
			for i in account_ids:
				account = {}
				account['account_id'] = i['id']
				account['account_name'] = i['name']
				accounts.append(account)

			return Response({'accounts': accounts, 'ad_platform': 'meta_ads'})
