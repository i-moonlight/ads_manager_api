# -*- coding: utf-8 -*-
#!/usr/bin/env python

from django.conf import settings
from urllib.parse import urlparse

import traceback

from api.google_ads.models import *
from api.ad_accounts.models import Authorizations

from decouple import config

import time
from datetime import datetime

from google.ads.googleads.client import GoogleAdsClient

#GOOGLE_CLIENT_ID = getattr(settings, 'GOOGLE_CLIENT_ID')
#GOOGLE_CLIENT_SECRET = getattr(settings, 'GOOGLE_CLIENT_SECRET')
GOOGLE_PROJECT_ID = getattr(settings, 'GOOGLE_PROJECT_ID')
#GOOGLE_DEVELOPER_TOKEN = getattr(settings, 'GOOGLE_DEVELOPER_TOKEN')
GOOGLE_JAVASCRIPT_ORIGINS = getattr(settings, 'GOOGLE_JAVASCRIPT_ORIGINS')

credentials={'developer_token':  getattr(settings, 'GOOGLE_DEVELOPER_TOKEN'),
			'use_proto_plus': True,
			'client_id':  getattr(settings, 'GOOGLE_CLIENT_ID'),
			'client_secret': getattr(settings, 'GOOGLE_CLIENT_SECRET'),
}


def import_google_ads_account_data(account_id, user_id):
	
	print('IMPORT GOOGLE ACCOUNT DATA')
	try:
		# https://developers.google.com/google-ads/api/docs/start

		authorization = Authorizations.objects.filter(user=user_id,ad_platform='google_ads').first()

		if authorization:
			 # Set import_start_date_time
			authorization.import_start_date_time = datetime.now()
			# Extract the values from the authorization object
			account_id = authorization.account_id
			access_token = authorization.access_token
			refresh_token = authorization.refresh_token

			print('account_id', account_id)
			print('access_token', access_token)
			print('refresh_token', refresh_token)
			
			credentials['refresh_token'] = refresh_token
			credentials['login_customer_id'] = account_id

			print('credentials', credentials)

			client = GoogleAdsClient.load_from_dict(credentials)
			
			#get_campaigns(client, account_id, user_id)
			#get_adsets(account, account_id, user_id)
			#get_ads(account, account_id, user_id, access_token)

			return {
				'message': 'Google Ads Data Imported Successfully',
				'ad_platform': 'google_ads',
				'is_importing': False,
			}
		else:
			return {
				'message': 'Authorization not found for Google Ads',
				'ad_platform': 'google_ads',
				'is_importing': False,
			}
			
	except Exception as e:
        # Handle any other exceptions here
		return {
          'message': f'Error: {str(e)}',
          'ad_platform': 'google_ads',
          'is_importing': False,
        }