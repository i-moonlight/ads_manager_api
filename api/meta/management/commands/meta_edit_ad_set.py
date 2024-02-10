# -*- coding: utf-8 -*-
#!/usr/bin/env python

import traceback

from api.meta.models import *
from api.ad_accounts.models import Authorizations

from django.conf import settings
from django.core.management.base import BaseCommand

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adset import AdSet
from facebook_business.exceptions import FacebookRequestError

from core.utils.slack import slack_alert_api_issue

from decouple import config

META_APP_ID = getattr(settings, 'META_APP_ID')
META_APP_SECRET = getattr(settings, 'META_APP_SECRET')


class Command(BaseCommand):
	help = 'This command does some thing'

	def handle(self, *args, **options):
		start_app()

def start_app():
	
	try:
		print('Start meta_edit_ad_set.py')
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


		ad_set_data = {}
		ad_set_data['meta_ad_set_id'] = 23858016660000568
		ad_set_data['name'] = 'Ad Set F UPDATED D'

		edit_ad_set(ad_set_data)
	
	except Exception as e:
		print(e)
		traceback.print_exc()  # Print the traceback information
		#slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		input('error A...')
		

def edit_ad_set(ad_set_data):

	print('edit ad_set')
	try:
		
		
		params = {
		}
		
		if ad_set_data.get('name'):
			params['name'] = ad_set_data['name']
		else:
			params['name'] = 'New Ad Set'

		if ad_set_data.get('objective'):
			params['objective'] = ad_set_data['objective']
		
		if ad_set_data.get('special_ad_categories'):
			params['special_ad_categories'] = ad_set_data['special_ad_categories']
		else:
			params['special_ad_categories'] = []

		if ad_set_data.get('bid_strategy'):
			params['bid_strategy'] = ad_set_data['bid_strategy']

		if ad_set_data.get('lifetime_budget'):
			params['lifetime_budget'] = ad_set_data['lifetime_budget']
		elif ad_set_data.get('daily_budget'):
			params['daily_budget'] = ad_set_data['daily_budget']

		if ad_set_data.get('start_time'):
			params['start_time'] = ad_set_data['start_time']

		if ad_set_data.get('stop_time'):
			params['stop_time'] = ad_set_data['stop_time']

		if ad_set_data.get('status'):
			params['status'] = ad_set_data['status']
		else:
			params['status'] = AdSet.Status.paused
		
		meta_ad_set_id = ad_set_data['meta_ad_set_id']
		ad_set = AdSet(meta_ad_set_id)

		ad_set.api_update(fields=[], params=params)

		fields = [		
			'id',
			'campaign_id',	
			'created_time',
			'budget_remaining',
			'daily_budget',
			'daily_min_spend_target',
			'daily_spend_cap',
			'end_time',
			'lifetime_budget',
			'lifetime_spend_cap',
			'name',
			'start_time',
			'status',
			'targeting',
		]

		ad_set_data_updated = ad_set.api_get(fields=fields)

		print(ad_set_data_updated)
		ad_set_name = ad_set_data_updated.get('name')
		print(ad_set_name)
		input('continue...')

	except FacebookRequestError as e:
		# Handle any Facebook API errors
		#print(e)
		error_message = e.api_error_message()
		error_code = e.api_error_code()
		error_subcode = e.api_error_subcode()
		error_type = e.api_error_type()
		print(f"Facebook API error occurred when editing ad set:")
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



