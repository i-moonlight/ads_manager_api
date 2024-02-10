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
import json
import uuid

client_id = getattr(settings, 'TIKTOK_APP_ID')
client_secret = getattr(settings, 'TIKTOK_APP_SECRET')
client_rid = getattr(settings, 'TIKTOK_APP_RID')


class Enable(LoggingMixin, APIView):
	def get(self, request):
		Authorizations.objects.filter(
			user=request.user, ad_platform='tiktok').delete()
		
		redirect_uri = getattr(settings, 'FE_SERVER') + '/ad-accounts'
		state = uuid.uuid4()
		state = str(state)
		print('client_id', client_id)
		print('state', state)
		print('redirect_uri', redirect_uri)
		print('client_rid', client_rid)
		authorization_url = 'https://ads.tiktok.com/marketing_api/auth?app_id=' + client_id  + '&state=' + state + '&redirect_uri=' + redirect_uri + '&rid=' + client_rid

		print(authorization_url)
		return Response({"authorization_url": authorization_url})


class DisableAPI(LoggingMixin, APIView):
	def delete(self, request):
		Authorizations.objects.filter(
			user=request.user, ad_platform='tiktok').delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


class Oauth(LoggingMixin, APIView):
	def post(self, request):
		try:
			auth_code = request.data.get("code")
			auth_code = str(auth_code)
			# Get Access token

			#redirect_uri = getattr(settings, 'FE_SERVER') + '/ad-accounts'

			access_token_url = 'https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/'

			payload = {
				'auth_code' : auth_code,
				'app_id' : client_id,
				'secret' : client_secret,
			}

			headers = {
				"Content-Type": "application/json",
			}

			response = requests.post(url=access_token_url, headers=headers, json=payload)
			token_info  = response.json()
			access_token = token_info['data']['access_token']

			authorization = Authorizations()
			authorization.user = request.user
			authorization.ad_platform = 'tiktok'
			authorization.access_token = access_token
			authorization.date_time = datetime.utcnow()
			authorization.save()

			advertiser_ids = token_info['data']['advertiser_ids']

			advertiser_ids = json.dumps(advertiser_ids)

			ad_account_details_url = 'https://business-api.tiktok.com/open_api/v1.3/advertiser/info/'
			params = {
				'advertiser_ids': advertiser_ids,				
			}

			headers = {
				"Access-Token": access_token,
			}

			response = requests.get(url=ad_account_details_url, headers=headers, params=params)

			account_details  = response.json()

			ad_accounts = account_details['data']['list']

			accounts=[]
			for i in ad_accounts:
				account = {}
				account['account_id'] = i['advertiser_id']
				account['account_name'] = i['name']
				accounts.append(account)
			
			if len(ad_accounts) == 1:
					account_id=ad_accounts[0]['advertiser_id']
					account_name=ad_accounts[0]['name']
					authorization.account_id = account_id
					authorization.account_name = account_name
					authorization.date_time = datetime.utcnow()
					#authorization.ip_address = "192.168.0.9"
					authorization.save()

			return Response({'accounts': accounts, 'ad_platform': 'tiktok'})

		except Exception as e:
			print(e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
			return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)