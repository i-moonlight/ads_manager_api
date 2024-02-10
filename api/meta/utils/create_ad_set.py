# -*- coding: utf-8 -*-
#!/usr/bin/env python
import traceback

from api.meta.models import *
from api.ad_accounts.models import Authorizations

from django.conf import settings

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.exceptions import FacebookRequestError

from core.utils.slack import slack_alert_api_issue

from django.core.management.base import BaseCommand

META_APP_ID = getattr(settings, 'META_APP_ID')
META_APP_SECRET = getattr(settings, 'META_APP_SECRET')


class Command(BaseCommand):
	help = 'This command adds a new ad set to a meta ads campaign'

	def handle(self, *args, **options):
		start_app()

def start_app():
	
	print('Start meta_create_ad_set.py')
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

	account = AdAccount('act_' + str(account_id))

	ad_set_data = {}
	ad_set_data['name'] = 'Link Clicks Test Ad Set F c'
	ad_set_data['campaign_id'] = 23857960349470568
	ad_set_data['dsa_beneficiary'] = 'Test DSA Beneficiary'
	ad_set_data['dsa_payor'] = 'Test DSA Payor'
	#ad_set_data['billing_event'] = 'IMPRESSIONS'
	
	
	create_ad_set(account, ad_set_data)


def create_ad_set(account, ad_set_data):

	print('create meta ad set')
	try:

		
		'''
		if ad_set_data.get('name'):
			params['name'] = ad_set_data['name']
		else:
			params['name'] = AdSet.BillingEvent.link_clicks

		if ad_set_data.get('billing_event'):
			params['billing_event'] = ad_set_data['billing_event']
		else:
			params['billing_event'] = AdSet.BillingEvent.link_clicks

		'''
		params = {
            'name': ad_set_data.get('name', 'New Ad Set'),
            'campaign_id': ad_set_data['campaign_id'],
	    	'billing_event': ad_set_data.get('billing_event', AdSet.BillingEvent.link_clicks),
		    'status': ad_set_data.get('status', 'PAUSED'),
		    'daily_budget': '1000',
		    'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
        }

		if ad_set_data.get('dsa_beneficiary'):
			params['dsa_beneficiary'] = ad_set_data['dsa_beneficiary']

		if ad_set_data.get('dsa_payor'):
			params['dsa_payor'] = ad_set_data['dsa_payor']


		params['targeting'] = {
				'geo_locations': {
					'country_groups': ['worldwide'],
					'countries': [],
				}
			}

		ad_set = account.create_ad_set(fields=[], params=params)

		# Get the ad set ID
		ad_set_id = ad_set.get_id()

		print('ad_set_id is', ad_set_id)
		
		return ad_set_id
	
	except FacebookRequestError as e:
		# Handle Facebook API errors
		#print(e)
		error_message = e.api_error_message()
		error_code = e.api_error_code()
		error_subcode = e.api_error_subcode()
		error_type = e.api_error_type()
		print(f"Facebook API error occurred when creating new ad set:")
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



