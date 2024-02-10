# -*- coding: utf-8 -*-
#!/usr/bin/env python
import traceback


from api.meta.models import *
from api.ad_accounts.models import Authorizations

from django.conf import settings
from django.core.management.base import BaseCommand

from decouple import config

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.exceptions import FacebookRequestError

from core.utils.slack import slack_alert_api_issue

META_APP_ID = getattr(settings, 'META_APP_ID')
META_APP_SECRET = getattr(settings, 'META_APP_SECRET')

class Command(BaseCommand):
	help = 'This command creates a new meta ads campaign'

	def handle(self, *args, **options):
		start_app()

def start_app():
	
	print('Start meta_create_campaign.py')
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

	campaign_data = {}
	campaign_data['name'] = 'Link Clicks Test Campaign E 2'
	campaign_data['objective'] = 'OUTCOME_TRAFFIC'  #OUTCOME_LEADS, OUTCOME_SALES, OUTCOME_ENGAGEMENT, OUTCOME_AWARENESS, OUTCOME_TRAFFIC, OUTCOME_APP_PROMOTION
	campaign_data['special_ad_categories'] = []
	#campaign_data['lifetime_budget'] = 10000
	#campaign_data['daily_budget'] = 1000
	#campaign_data['spend_cap'] = 10000
	#campaign_data['start_time'] = '2023-08-08'
	#campaign_data['stop_time'] = '2023-09-09'
	#campaign_data['status'] = 'PAUSED'
	#campaign_data['bid_strategy'] = 'LOWEST_COST_WITHOUT_CAP'
	#campaign_data['can_use_spend_cap'] = True
	
	create_campaign(account, campaign_data)


def create_campaign(account, campaign_data):

	print('create campaign')
	try:
		
		fields = [
		]
		params = {
		}

		if campaign_data.get('name'):
			params['name'] = campaign_data['name']
		else:
			params['name'] = 'New Campaign'

		if campaign_data.get('objective'):
			params['objective'] = campaign_data['objective']
		else:
			params['objective'] = Campaign.Objective.outcome_traffic

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


		campaign = account.create_campaign(fields, params)

		# Get the campaign ID
		meta_campaign_id = campaign[Campaign.Field.id]

		print('campaign_id is', meta_campaign_id)

		'''
		meta_campaign = MetaCampaigns.objects.create(
			user_id=user_id,
			campaign_id=campaign_id,
			meta_campaign_id=meta_campaign_id,
			name=name,
			daily_budget=daily_budget,
			lifetime_budget=lifetime_budget,
			start_time=start_time,
			stop_time=stop_time,
			special_ad_categories=special_ad_categories,
			created_time=created_time,
			status=status,
			bid_strategy=bid_strategy,
			spend_cap=spend_cap,
			can_use_spend_cap=can_use_spend_cap,
			objective=objective
		)

		print(f"Inserted new campaign with id: {meta_campaign_id}")
		'''
		
	except FacebookRequestError as e:
		# Handle Facebook API errors
		#print(e)
		error_message = e.api_error_message()
		error_code = e.api_error_code()
		error_subcode = e.api_error_subcode()
		error_type = e.api_error_type()
		print(f"Facebook API error occurred when creating new campaign:")
		print(f"Message: {error_message}")
		print(f"Error Code: {error_code}")
		print(f"Error Subcode: {error_subcode}")
		print(f"Error Type: {error_type}")
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.


	except Exception as e:
		print(e)
		traceback.print_exc()  # Print the traceback information
		#slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		input('error...')
		return True



