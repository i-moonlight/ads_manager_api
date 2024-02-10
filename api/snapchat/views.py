from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin
import requests
import os

import sys
from ..ad_accounts.models import Authorizations
from .models import *
from datetime import datetime, timedelta


client_id = getattr(settings, 'SNAPCHAT_ADS_MANAGER_CLIENT_ID')
client_secret = getattr(settings, 'SNAPCHAT_ADS_MANAGER_CLIENT_SECRET')


class Enable(LoggingMixin, APIView):
	def get(self, request):
		Authorizations.objects.filter(
			user=request.user, ad_platform='snapchat').delete()
		
		redirect_uri = getattr(settings, 'FE_SERVER') + '/ad-accounts'

		authorization_url = 'https://accounts.snapchat.com/accounts/oauth2/auth?client_id=' + client_id + '&redirect_uri=' + redirect_uri + '&response_type=code&scope=snapchat-marketing-api'

		print(authorization_url)
		return Response({"authorization_url": authorization_url})


class DisableAPI(LoggingMixin, APIView):
	def delete(self, request):
		Authorizations.objects.filter(
			user=request.user, ad_platform='snapchat').delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


class Oauth(LoggingMixin, APIView):
	def post(self, request):
		try:
			code = request.data.get("code")
			code = str(code)

			# Get Access token

			redirect_uri = getattr(settings, 'FE_SERVER') + '/ad-accounts'

			access_token_url = 'https://accounts.snapchat.com/login/oauth2/access_token'

			payload = {
				"code" : code,
				"client_id" : client_id,
				"client_secret" : client_secret,
				"grant_type" : "authorization_code",
				"redirect_uri" : redirect_uri,
			}

			response = requests.post(url=access_token_url, data=payload)
			token_info  = response.json()

			access_token = token_info['access_token']
			expires_in = token_info['expires_in']
			access_token_expiry = datetime.utcnow() + timedelta(seconds=expires_in) 
			refresh_token = token_info['refresh_token']

			authorization = Authorizations()
			authorization.user = request.user
			authorization.ad_platform = 'snapchat'
			authorization.refresh_token = refresh_token
			authorization.access_token = access_token
			authorization.access_token_expiry = access_token_expiry
			authorization.date_time = datetime.utcnow()
			authorization.save()

			ad_account_details_url = 'https://adsapi.snapchat.com/v1/me/organizations'

			params = {
				"with_ad_accounts": True
			}
		
			bearer_token = "Bearer " + str(access_token)
			
			headers = {
				"Authorization": bearer_token,
			}


			response = requests.get(url=ad_account_details_url, headers=headers, params=params)
			account_details  = response.json()

			organizations =  account_details['organizations']

			accounts=[]

			for organization in organizations:			
				account_ids = organization['organization']['ad_accounts']

				for i in account_ids:
					account = {}
					account['account_id'] = i['id']
					account['account_name'] = i['name']
					accounts.append(account)
			
			if len(account_ids) == 1:
					account_id = i['id']
					account_name = i['name']
					authorization.account_id = account_id
					authorization.account_name = account_name
					authorization.date_time = datetime.utcnow()
					#authorization.ip_address = "192.168.0.9"
					authorization.save()

			return Response({'accounts': accounts, 'ad_platform': 'snapchat'})
		except Exception as e:
			print(e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
			return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)