# -*- coding: utf-8 -*-
#!/usr/bin/env python
import traceback

from api.meta.models import *

from django.conf import settings

from datetime import datetime

from facebook_business.adobjects.campaign import Campaign
from facebook_business.exceptions import FacebookRequestError

from core.utils.slack import slack_alert_api_issue

META_APP_ID = getattr(settings, 'META_APP_ID')
META_APP_SECRET = getattr(settings, 'META_APP_SECRET')


def create_campaign(user_id, campaign_id, account, campaign_data):

	print('meta create_campaign start')
	print('meta create_campaign campaign_data', campaign_data)
	print('campaign_id', campaign_id)
	print('user_id', user_id)
	try:
		
		fields = [
		]
		params = {
		}

		if campaign_data.get('name'):
			name = campaign_data['name']
		else:
			name = 'New Campaign'
		params['name'] = name
			
		if campaign_data.get('objective'):
			objective = campaign_data['objective']			
		else:
			objective = Campaign.Objective.outcome_traffic
		params['objective'] = objective

		if campaign_data.get('special_ad_categories'):
			special_ad_categories = campaign_data['special_ad_categories']			
		else:
			special_ad_categories = []		
		params['special_ad_categories'] = special_ad_categories

		if campaign_data.get('bid_strategy'):
			bid_strategy = campaign_data['bid_strategy']
			params['bid_strategy'] = bid_strategy
		else:
			bid_strategy = None

		daily_budget = None
		lifetime_budget = None
		if campaign_data.get('lifetime_budget'):
			lifetime_budget = campaign_data['lifetime_budget']
			params['lifetime_budget'] = lifetime_budget
		elif campaign_data.get('daily_budget'):
			daily_budget = campaign_data['daily_budget']
			params['daily_budget'] = daily_budget

		if campaign_data.get('start_time'):
			start_time = campaign_data['start_time']
		else:
			start_time = None
		params['start_time'] = start_time

		if campaign_data.get('stop_time'):
			stop_time = campaign_data['stop_time']
		else:
			stop_time = None
		params['stop_time'] = stop_time

		if campaign_data.get('status'):
			status = campaign_data['status']
		else:
			status = Campaign.Status.paused
		params['status'] = status

		#if campaign_data['spend_cap']:
		#	params['spend_cap'] = campaign_data['spend_cap']

		#if campaign_data['can_use_spend_cap']:
		#	params['can_use_spend_cap'] = campaign_data['can_use_spend_cap']

		campaign = account.create_campaign(fields, params)

		# Get the campaign ID
		meta_campaign_id = campaign[Campaign.Field.id]

		print('meta_campaign_id is', meta_campaign_id)

		
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
			created_time=datetime.now(),
			status=status,
			bid_strategy=bid_strategy,
			objective=objective
		)

		print(f"Inserted new campaign with id: {meta_campaign_id}")
		
		
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
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		input('meta create_campaign error...')
		return True



