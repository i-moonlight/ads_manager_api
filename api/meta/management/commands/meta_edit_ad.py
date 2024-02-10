# -*- coding: utf-8 -*-
#!/usr/bin/env python

import traceback

from api.meta.models import *
from api.ad_accounts.models import Authorizations

from django.conf import settings
from django.core.management.base import BaseCommand

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.ad import Ad
from facebook_business.exceptions import FacebookRequestError

from core.utils.slack import slack_alert_api_issue

from decouple import config

META_APP_ID = getattr(settings, 'META_APP_ID')
META_APP_SECRET = getattr(settings, 'META_APP_SECRET')

class Command(BaseCommand):
	help = 'This command edits an ad.'

	def handle(self, *args, **options):
		start_app()

def start_app():
	
	try:
		print('Start meta_edit_ad.py')
		# Retrieve data from the AdAccountsAuthorizations table
		authorization = Authorizations.objects.get(ad_platform='meta_ads')
		
		# Extract the values from the authorization object
		account_id = authorization.account_id
		access_token = authorization.access_token
		user_id = authorization.user_id

		print('account_id is', account_id)
		print('access_token is', access_token)
		print('user_id is', user_id)

		FacebookAdsApi.init(META_APP_ID, META_APP_SECRET, access_token)


		ad_data = {}
		ad_data['meta_ad_id'] = 23858458489030568
		ad_data['name'] = 'Test Ad C 3'
		ad_data['status'] = 'PAUSED'

		edit_ad(ad_data)
	
	except Exception as e:
		print(e)
		traceback.print_exc()  # Print the traceback information
		#slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		input('error A...')
		

def edit_ad(ad_data):

	print('edit ad')
	try:
		
		
		params = {
		}
		
		if ad_data.get('name'):
			params['name'] = ad_data['name']
		else:
			params['name'] = 'New Ad'
		
		if ad_data.get('status'):
			params['status'] = ad_data['status']
		else:
			params['status'] = Ad.Status.paused
		
		meta_ad_id = ad_data['meta_ad_id']
		ad = Ad(meta_ad_id)

		ad.api_update(fields=[], params=params)

		fields = [			
			'id',
			'ad_review_feedback',
			'adset_id',
			'bid_amount',
			'campaign_id',
			'created_time',
			'creative',
			'effective_status',
			'issues_info',
			'name',
			'preview_shareable_link',
			'status',
			'tracking_specs',
			'updated_time',
		]

		ad_data_updated = ad.api_get(fields=fields)

		print(ad_data_updated)
		ad_name = ad_data_updated.get('name')
		print(ad_name)
		input('continue...')

	except FacebookRequestError as e:
		# Handle any Facebook API errors
		#print(e)
		error_message = e.api_error_message()
		error_code = e.api_error_code()
		error_subcode = e.api_error_subcode()
		error_type = e.api_error_type()
		print(f"Facebook API error occurred when editing ad:")
		print(f"Message: {error_message}")
		print(f"Error Code: {error_code}")
		print(f"Error Subcode: {error_subcode}")
		print(f"Error Type: {error_type}")
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
	
	except Exception as e:
		print(e)
		traceback.print_exc()  # Print the traceback information
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		input('error...')
		return True



