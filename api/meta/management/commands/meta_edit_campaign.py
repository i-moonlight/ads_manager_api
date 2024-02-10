# -*- coding: utf-8 -*-
#!/usr/bin/env python

import traceback

from api.meta.models import *
from api.ad_accounts.models import Authorizations

from django.conf import settings
from django.core.management.base import BaseCommand

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.campaign import Campaign
from facebook_business.exceptions import FacebookRequestError

from core.utils.slack import slack_alert_api_issue

from decouple import config

META_APP_ID = getattr(settings, 'META_APP_ID')
META_APP_SECRET = getattr(settings, 'META_APP_SECRET')

class Command(BaseCommand):
	help = 'This command edits a meta ads campaign'

	def handle(self, *args, **options):
		start_app()

def start_app():
	
	try:
		print('Start meta_edit_campaign.py')
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


		campaign_data = {}
		campaign_data['meta_campaign_id'] = 23857960349470568
		campaign_data['name'] = 'Campaign E UPDATED 3'
		#campaign_data['objective'] = 'OUTCOME_TRAFFIC'  #OUTCOME_LEADS, OUTCOME_SALES, OUTCOME_ENGAGEMENT, OUTCOME_AWARENESS, OUTCOME_TRAFFIC, OUTCOME_APP_PROMOTION
		#campaign_data['special_ad_categories'] = []
		#campaign_data['lifetime_budget'] = 10000
		#campaign_data['daily_budget'] = 100
		#campaign_data['spend_cap'] = 10000
		#campaign_data['start_time'] = '2023-08-08T00:00:00-0500'
		#campaign_data['stop_time'] = '2023-09-09'
		#campaign_data['status'] = 'PAUSED'
		#campaign_data['bid_strategy'] = 'LOWEST_COST_WITHOUT_CAP'
		#campaign_data['can_use_spend_cap'] = True
		
		
		edit_campaign(campaign_data)
	
	except Exception as e:
		print(e)
		traceback.print_exc()  # Print the traceback information
		#slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		input('error A...')
		



def edit_campaign(campaign_data):

	print('edit campaign')
	try:
		
		params = {
		}
		
		if campaign_data.get('name'):
			params['name'] = campaign_data['name']
		else:
			params['name'] = 'New Campaign'

		if campaign_data.get('objective'):
			params['objective'] = campaign_data['objective']
		
		if campaign_data.get('special_ad_categories'):
			params['special_ad_categories'] = campaign_data['special_ad_categories']
		else:
			params['special_ad_categories'] = []

		if campaign_data.get('bid_strategy'):
			params['bid_strategy'] = campaign_data['bid_strategy']

		if campaign_data.get('lifetime_budget'):
			params['lifetime_budget'] = campaign_data['lifetime_budget']
		elif campaign_data.get('daily_budget'):
			params['daily_budget'] = campaign_data['daily_budget']

		if campaign_data.get('start_time'):
			params['start_time'] = campaign_data['start_time']

		if campaign_data.get('stop_time'):
			params['stop_time'] = campaign_data['stop_time']

		if campaign_data.get('status'):
			params['status'] = campaign_data['status']
		else:
			params['status'] = Campaign.Status.paused

		#if campaign_data['spend_cap']:
		#	params['spend_cap'] = campaign_data['spend_cap']

		#if campaign_data['can_use_spend_cap']:
		#	params['can_use_spend_cap'] = campaign_data['can_use_spend_cap']

		meta_campaign_id = campaign_data['meta_campaign_id']
		campaign = Campaign(meta_campaign_id)

		campaign.api_update(fields=[], params=params)

		fields = [
			'name',
			'objective',
			'status',
			'bid_strategy',
			'buying_type',
			'last_budget_toggling_time',
			'lifetime_budget',
			'daily_budget',
			'budget_remaining',
			'spend_cap',
			'can_use_spend_cap',
			'issues_info',
			'start_time',
			'stop_time',
			'status',
			'configured_status',
			'effective_status',
			'special_ad_categories',
			'special_ad_category',	
			'created_time',		
		]

		campaign_data_updated = campaign.api_get(fields=fields)

		print(campaign_data_updated)
		campaign_name = campaign_data_updated.get('name')
		print(campaign_name)
		input('continue...')

	except FacebookRequestError as e:
		# Handle any Facebook API errors
		#print(e)
		error_message = e.api_error_message()
		error_code = e.api_error_code()
		error_subcode = e.api_error_subcode()
		error_type = e.api_error_type()
		print(f"Facebook API error occurred when editing campaign:")
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



