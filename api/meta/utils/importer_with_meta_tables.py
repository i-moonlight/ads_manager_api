# -*- coding: utf-8 -*-
#!/usr/bin/env python
from PIL import Image
import requests
from io import BytesIO

from urllib.parse import urlparse
import os
import sys
import ast
import traceback

import json
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.exceptions import ObjectDoesNotExist

from api.meta.models import *
from api.ad_accounts.models import Authorizations
from api.ad_manager.models import Campaigns, CampaignsPlatforms, AdSets, AdSetsPlatforms, AdSetsKeywords, AdSetsLanguages, AdSetsLocations, Ads, AdsPerformance, AdsPlatforms
from api.media_library.models import Media

import time
from datetime import datetime, date, timedelta


from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.ad import Ad

from core.utils.slack import slack_alert_api_issue

META_APP_ID = getattr(settings, 'META_APP_ID')
META_APP_SECRET = getattr(settings, 'META_APP_SECRET')
META_SYSTEM_USER_ACCESS_TOKEN = getattr(settings, 'META_SYSTEM_USER_ACCESS_TOKEN')
META_API_VERSION = getattr(settings, 'META_API_VERSION')

throttle_delay = 10 #set a time to throttle API calls that have exceeded limits
data_days = 365*5 #set the number of days of data to retrieve

def import_meta_account_data(account_id, user_id):
	print('START IMPORT META ACCOUNT DATA')
	try:
		# Get the authorization object
		authorization = Authorizations.objects.filter(user=user_id, ad_platform='meta_ads').first()
		#print('sleeping for 20 seconds...')
		#ime.sleep(20)
		if authorization:
			# Set import_start_date_time
			authorization.import_start_date_time = datetime.now()

			access_token = authorization.access_token

			# Initialize FacebookAdsApi with the retrieved access_token
			FacebookAdsApi.init(META_APP_ID, META_APP_SECRET, access_token)

			account = AdAccount('act_' + str(account_id))

			print('account_id is ', account_id)
			get_campaigns(account, account_id, user_id)
			get_adsets(account, user_id)
			get_ads(account, account_id, user_id, access_token)

			# Set import_end_date_time and is_imported
			authorization.import_end_date_time = datetime.now()
			authorization.is_imported = True

			# Save the updated authorization object
			authorization.save()

			return {
				'message': 'Meta Ads Data Imported Successfully',
				'ad_platform': 'meta_ads',
				'is_importing': False,
			}
		else:
			return {
				'message': 'Authorization not found for Meta Ads',
				'ad_platform': 'meta_ads',
				'is_importing': False,
			}
	except Exception as e:
		# Handle any other exceptions here
		return {
			'message': f'Error: {str(e)}',
			'ad_platform': 'meta_ads',
			'is_importing': False,
		}


def check_api_usage(headers, account_id):
	# Access the response headers get usage limit data

	try:
		if	'x-business-use-case-usage' in headers:
			usage_data = headers['x-business-use-case-usage']
			usage_data = json.loads(usage_data)
			print('\033[93m x-business-use-case-usage', usage_data, ' \033[0m')
			print('usage_data is ', usage_data)
			print('account_id is ', account_id)
			usage_data = usage_data[account_id][0]

		else:
			print("\033[93m x-business-use-case-usage header not present \033[0m")

		if 'x-ad-account-usage' in headers:
			print('\033[93m x-ad-account-usage', headers['x-ad-account-usage'], ' \033[0m')
		else:
			print("\033[93m x-ad-account-usage header not present \033[0m")

		if 'x-app-usage' in headers:
			usage_data = headers['x-app-usage']
			usage_data = json.loads(usage_data)
			print('\033[93m x-app-usage', usage_data, ' \033[0m')
		else:
			print("\033[93m x-app-usage header not present \033[0m")

		print('usage_data is ', usage_data)
		if usage_data:
			call_count = usage_data['call_count']
			if call_count > 75:
				print('\033[91m  call_count', call_count, ' \033[0m')
				print("\033[91m call_count over 75% - slowing down import \033[0m")
				print('pausing for ' + str(throttle_delay) + ' seconds...')
				time.sleep(throttle_delay) # Introduce a delay
			else:
				print('\033[92m  call_count', call_count, ' \033[0m')

			total_cputime = usage_data['total_cputime']
			if total_cputime > 75:
				print('\033[91m  total_cputime', total_cputime, ' \033[0m')
				print("\033[91m total_cputime over 75% - slowing down import \033[0m")
				print('pausing for ' + str(throttle_delay) + ' seconds...')
				time.sleep(throttle_delay) # Introduce a delay
			else:
				print('\033[92m  total_cputime', total_cputime, ' \033[0m')

			total_time = usage_data['total_time']
			if total_time > 75:
				print('\033[91m  total_time', total_time, ' \033[0m')
				print("\033[91m total_time over 75% - slowing down import \033[0m")
				print('pausing for ' + str(throttle_delay) + ' seconds...')
				time.sleep(throttle_delay) # Introduce a delay
			else:
				print('\033[92m  total_time', total_time, ' \033[0m')

			if 'estimated_time_to_regain_access' in usage_data:
				time_to_regain_access = usage_data['estimated_time_to_regain_access']
				print('estimated_time_to_regain_access', time_to_regain_access)
				time_to_regain_access = int(time_to_regain_access)
				if time_to_regain_access > 0:
					print('pausing for ' + str(time_to_regain_access) + ' seconds...')
					time.sleep(time_to_regain_access)

		return True
	except Exception as e:
		print('error getting usage data', e)
		traceback.print_exc()  # Print the traceback information
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		return False


def get_campaigns(account, account_id, user_id):
	
	limit = 1000
	#request_interval = .5 # Delay between API requests in seconds

	while True:
		try:
			
			#https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group
			
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
				'upstream_events',			
				]
			
			'''
			params = {
				'effective_status': ['ACTIVE','PAUSED'],
				'limit': limit,
			}'''

			# Get today's date
			current_date = date.today()

			# Calculate the start date (2 years ago)
			start_date = current_date - timedelta(days=data_days)

			# Convert dates to string format for the API
			time_range = {
				'since': start_date.strftime('%Y-%m-%d'),
				'until': current_date.strftime('%Y-%m-%d'),
			}

			params = {
				'filtering': '[{"field":"ad.impressions","operator":"GREATER_THAN","value":0}]',
				'limit': limit,
				'time_range': time_range,
			}

			campaigns = account.get_campaigns(fields=fields, params=params)
			
			# Access the response headers get usage limit data
			# https://developers.facebook.com/docs/graph-api/overview/rate-limiting#ads-management
			headers = campaigns.headers()
			print(headers)
			print('get_campaigns')
			check_api_usage(headers, account_id)
			

			while True:
				#print(campaigns)
				for campaign in reversed(campaigns):
					
					#print(campaign)
					#('next')
					meta_campaign_id = campaign['id']
					campaign_id = update_or_create_campaign(campaign, user_id)
					#get_campaign_insights(meta_campaign_id, campaign_id)

				# Retrieve the next page of campaigns
				if campaigns.load_next_page():
					#time.sleep(request_interval)  # Introduce a delay
					continue
				else:
					break
			
		except Exception as e:
			print(e)
			traceback.print_exc()  # Print the traceback information
			slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
			print('pausing for ' + str(throttle_delay) + ' seconds...')
			time.sleep(throttle_delay) # Introduce a delay
			continue
		break


def update_or_create_campaign(campaign_data, user_id):
	"""
	This function updates or creates a new entry in the meta_campaigns table
	based on the provided campaign_data.
	"""
	try:
		# Fetch the User instance
		print('update or create campaign..')
		print(campaign_data)
		meta_campaign_id = campaign_data['id']
		name = campaign_data['name']
		objective = campaign_data['objective']
		status = campaign_data['status']
		
		if status == 'PAUSED':
			disabled = True
		else:
			disabled = False

		budget_remaining = campaign_data.get('budget_remaining')
		lifetime_budget = campaign_data.get('lifetime_budget')
		daily_budget = campaign_data.get('daily_budget')
		start_time = campaign_data.get('start_time')
		stop_time = campaign_data.get('stop_time')

		start_date = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S%z').date() if start_time else None
		end_date = datetime.strptime(stop_time, '%Y-%m-%dT%H:%M:%S%z').date() if stop_time else None

		special_ad_categories = campaign_data.get('special_ad_categories')
		credit = 'credit' in special_ad_categories
		employment = 'employment' in special_ad_categories
		housing = 'housing' in special_ad_categories
		social = 'social' in special_ad_categories
		special_ad_categories = str(special_ad_categories) if special_ad_categories else None
		created_time = campaign_data.get('created_time')
		bid_strategy = campaign_data.get('bid_strategy')
		spend_cap = campaign_data.get('spend_cap')
		can_use_spend_cap = campaign_data.get('can_use_spend_cap')
		
		budget = spend_cap if lifetime_budget is None and can_use_spend_cap else lifetime_budget
	
		campaign_platform = CampaignsPlatforms.objects.filter(
			campaign__user_id=user_id,
			api_id=meta_campaign_id,
			ad_platform='meta_ads'
		).first()

		if campaign_platform is None:
			print('no campaign')
			# Campaign does not exist, insert new entry

			campaign = Campaigns.objects.create(
				user=user_id,
				name=name,
				budget=budget,
				daily_budget=daily_budget,
				start_date=start_date,
				end_date=end_date,
				credit=credit,
				employment=employment,
				housing=housing,
				social=social,
				status=status,
				disabled=disabled,
				is_deleted=False
			)
			campaign_id = campaign.id

			print(f"New Campaign ID is {campaign_id}")

			meta_campaign = MetaCampaigns.objects.create(
				user=user_id,
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
		else:
			print('Campaign Exists!')
			campaign_id = campaign_platform.campaign_id

			# Campaign already exists, update existing entry
			meta_campaign = MetaCampaigns.objects.filter(meta_campaign_id=meta_campaign_id).update(
				name=name,
				daily_budget=daily_budget,
				lifetime_budget=lifetime_budget,
				start_time=start_time,
				stop_time=stop_time,
				special_ad_categories=special_ad_categories,
				status=status,
				bid_strategy=bid_strategy,
				spend_cap=spend_cap,
				objective=objective,
				meta_account_id=Authorizations.objects.filter(user=user_id,ad_platform='meta_ads').first().account_id
			)
			#print(f"Updated meta campaign with meta_campaign_id: {meta_campaign_id}")

			campaign = Campaigns.objects.filter(id=campaign_id).update(
				name=name,
				budget=budget,
				daily_budget=daily_budget,
				start_date=start_date,
				end_date=end_date,
				credit=credit,
				employment=employment,
				housing=housing,
				social=social,
				status=status,
				disabled=disabled,
				is_deleted=False
			)
		
			#print(f"Updated campaign with campaign_id: {campaign_id}")
		
		publisher_platforms = ['audience_network', 'facebook', 'instagram', 'messenger']
		for publisher_platform in publisher_platforms:

			campaign_platform_instance, created = 	CampaignsPlatforms.objects.get_or_create(
				campaign_id=campaign_id,
				publisher_platform=publisher_platform,
				api_id=meta_campaign_id,
				ad_platform='meta_ads',
			)
		
			if created:
				campaign_platform_instance.disabled = disabled
				campaign_platform_instance.previously_disabled = disabled
				campaign_platform_instance.status = status
				campaign_platform_instance.save()

		return campaign_id

	except Exception as e:
		print(e)
		traceback.print_exc()  # Print the traceback information
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		return False


def get_adsets(account, user_id):
	
	# https://developers.facebook.com/docs/marketing-api/reference/ad-campaign
	
	limit = 1000
	
	print('start get_adsets')
	while True:	
		try:
		
			"""
			fields = [
				'adlabels',
				'adset_schedule',
				'attribution_spec',
				'bid_adjustments',
				'bid_amount',
				'bid_constraints',
				'bid_info',
				'bid_strategy',
				'billing_event',
				'budget_remaining',
				'campaign_id',
				'configured_status',
				'created_time',
				'creative_sequence',
				'daily_budget',
				'daily_min_spend_target',
				'daily_spend_cap',
				'destination_type',
				'effective_status',
				'end_time',
				'frequency_control_specs',
				'id',
				'instagram_actor_id',
				'issues_info',
				'learning_stage_info',
				'lifetime_budget',
				'lifetime_min_spend_target',
				'lifetime_spend_cap',
				'multi_optimization_goal_weight',
				'name',
				'optimization_goal',
				'optimization_sub_event',
				'recurring_budget_semantics',
				'start_time',
				'status',
				'targeting',
				] 
			"""
			
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
			'''
			params = {
				'effective_status': ['ACTIVE', 'PAUSED', 'PENDING_REVIEW', 'DISAPPROVED', 'PREAPPROVED', 'PENDING_BILLING_INFO', 'CAMPAIGN_PAUSED', 'ADSET_PAUSED', 'IN_PROCESS', 'WITH_ISSUES'],
				'limit': limit,
			}'''
			
		
			# Get today's date
			current_date = date.today()

			# Calculate the start date (2 years ago)
			start_date = current_date - timedelta(days=data_days)

			# Convert dates to string format for the API
			time_range = {
				'since': start_date.strftime('%Y-%m-%d'),
				'until': current_date.strftime('%Y-%m-%d'),
			}

			
			params = {
				'filtering': '[{"field":"ad.impressions","operator":"GREATER_THAN","value":0}]',
				'limit': limit,
				'time_range': time_range,
			}

			
			ad_sets = account.get_ad_sets(fields=fields, params=params)

			print('ad_sets', ad_sets)
			# Access the response headers get usage limit data
			headers = ad_sets.headers()
			print(headers)
			
			account_usage = headers['x-ad-account-usage']
			account_usage = json.loads(account_usage)
			acc_id_until_pct = account_usage['acc_id_util_pct']
			print('acc_id_until_pct', acc_id_until_pct)

			app_usage = headers['x-app-usage']
			app_usage = json.loads(app_usage)
			call_count = app_usage['call_count']
			if call_count > 90:
				print('\033[91m  call_count', call_count, ' \033[0m')
				print("\033[91m call_count over 90% - slowin down ad set import \033[0m")
				print('pausing for ' + str(throttle_delay) + ' seconds...')
				time.sleep(throttle_delay) # Introduce a delay
			else:
				print('\033[92m  call_count', call_count, ' \033[0m')

			total_cputime = app_usage['total_cputime']
			if total_cputime > 90:
				print('\033[91m  total_cputime', total_cputime, ' \033[0m')
				print("\033[91m total_cputime over 90% - slowin down ad set import \033[0m")
				print('pausing for ' + str(throttle_delay) + ' seconds...')
				time.sleep(throttle_delay) # Introduce a delay
			else:
				print('\033[92m  total_cputime', total_cputime, ' \033[0m')

			total_time = app_usage['total_time']
			if total_time > 90:
				print('\033[91m  total_time', total_time, ' \033[0m')
				print("\033[91m total_time over 90% - slowin down ad set import \033[0m")
				print('pausing for ' + str(throttle_delay) + ' seconds...')
				time.sleep(throttle_delay) # Introduce a delay
			else:
				print('\033[92m  total_time', total_time, ' \033[0m')

			
			if 'x-fb-insights-stability-throttle' in headers:
				insights_stability_throttle = headers['x-fb-insights-stability-throttle']
				insights_stability_throttle = json.loads(insights_stability_throttle)
				throttled = insights_stability_throttle['throttled']
				print('throttled', throttled)
				if throttled == True:
					print("\033[91m throttled - slowing down ad set import \033[0m")
					print('pausing for ' + str(throttle_delay) + ' seconds...')
					time.sleep(throttle_delay) # Introduce a delay

				print(insights_stability_throttle)
				complexity_score = insights_stability_throttle['backend_qps']['actual_score']
				print('complexity_score', complexity_score)
				complexity_limit = insights_stability_throttle['backend_qps']['limit']
				print('complexity_limit', complexity_limit)
				
				if complexity_score/complexity_limit > .9:
					print("\033[91m Complexity score near limit. Slowing down campaign import \033[0m")
					print('pausing for ' + str(throttle_delay) + ' seconds...')
					time.sleep(throttle_delay) # Introduce a delay
				else:
					print('\033[92m  complexity ratio', complexity_score/complexity_limit, ' \033[0m')
			else:
				print("\033[93m x-fb-insights-stability-throttle header not present \033[0m")

			#input('ad sets retrieved...next..')

			while True:
				#print(ad_sets)
				for ad_set in ad_sets:
					#print(ad_set)
					ad_set_id = update_or_create_ad_set(ad_set, user_id)
					# get_ad_set_insights(meta_ad_set_id, ad_set_id)
					#input('next ad set..')
				# Retrieve the next page of ad sets
				if ad_sets.load_next_page():
					continue
				else:
					break
			
		except Exception as e:
			print("Error in get_adsets: ",e)
			traceback.print_exc()  # Print the traceback information
			slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
			print('pausing for ' + str(throttle_delay) + ' seconds...')
			time.sleep(throttle_delay) # Introduce a delay
			continue
		break


def update_or_create_ad_set(ad_set, user_id):
	"""
	This function updates or creates a new entry in the meta_ad_sets table
	based on the provided campaign_id.
	"""
	try:
		#print('update or create ad set')
		meta_ad_set_id = ad_set['id']
		meta_campaign_id = ad_set['campaign_id']
		name = ad_set['name']
		status = ad_set['status']
		disabled = status == 'PAUSED'
		daily_budget = ad_set.get('daily_budget')
		daily_spend_cap = ad_set.get('daily_spend_cap')
		lifetime_budget = ad_set.get('lifetime_budget')
		start_time = ad_set.get('start_time')
		start_date = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S%z').date() if start_time else None
		stop_time = ad_set.get('stop_time')
		end_date = datetime.strptime(stop_time, '%Y-%m-%dT%H:%M:%S%z').date() if stop_time else None

		targeting = None
		age_max = None
		age_min = None
		gender = None
		publisher_platforms = ['audience_network', 'facebook', 'instagram', 'messenger']

		if 'targeting' in ad_set:
			targeting = ad_set['targeting']
			print('adset targeting', targeting)

			age_max = targeting.get('age_max')
			age_min = targeting.get('age_min')
			gender = targeting['genders'][0] if 'genders' in targeting else None

			interests = targeting['flexible_spec'][0]['interests'] if 'flexible_spec' in targeting and 'interests' in targeting['flexible_spec'][0] else None

			geo_locations = targeting.get('geo_locations')
			if geo_locations:
				countries = geo_locations.get('countries')
				cities = geo_locations.get('cities')
				regions = geo_locations.get('regions')
				zips = geo_locations.get('zips')
				custom_locations = geo_locations.get('custom_locations')
				geo_markets = geo_locations.get('geo_markets')
				location_types = geo_locations.get('location_types')
				excluded_geo_locations = geo_locations.get('excluded_geo_locations')
			else:
				countries = cities = regions = zips = custom_locations = geo_markets = location_types = excluded_geo_locations = None

			if regions is not None:
				print('\033[91m regions exist\033[0m')

			if geo_markets is not None:
				print('\033[91m geo_markets exists \033[0m')

			if zips is not None:
				print('\033[91m geo_markets exists \033[0m')

			locales = targeting.get('locales')
			publisher_platforms_enabled = targeting.get('publisher_platforms', ['audience_network', 'facebook', 'instagram', 'messenger'])
			audience_network_positions = targeting.get('audience_network_positions')
			facebook_positions = targeting.get('facebook_positions')
			instagram_positions = targeting.get('instagram_positions')
			messenger_positions = targeting.get('messenger_positions')

		created_time = ad_set.get('created_time')

		campaign_id = CampaignsPlatforms.objects.filter(
			campaign__user_id=user_id,
			api_id=meta_campaign_id,
			ad_platform='meta_ads'
		).values_list('campaign_id', flat=True).first()

		
		ad_set_platform = AdSetsPlatforms.objects.filter(
			ad_set__user_id=user_id,
			api_id=meta_ad_set_id,
			ad_platform='meta_ads'
		).first()

		if ad_set_platform is None:
			print('no ad_set')

			ad_set = AdSets.objects.create(
				user=user_id,
				campaign_id=campaign_id,
				name=name,
				spend_limit=lifetime_budget,
				age_min=age_min,
				age_max=age_max,
				gender=gender,
				created=created_time,
				status=status,
				disabled=disabled,
				is_deleted=False
			)

			ad_set_id = ad_set.id

			#print(f"New Ad Set ID is {ad_set_id}")
			
			meta_ad_set = MetaAdSets.objects.create(
				user=user_id,
				ad_set_id=ad_set_id,
				campaign_id=campaign_id,
				meta_ad_set_id=meta_ad_set_id,
				meta_campaign_id=meta_campaign_id,
				name=name,
				daily_budget=daily_budget,
				daily_spend_cap=daily_spend_cap,
				lifetime_budget=lifetime_budget,
				start_time=start_time,
				end_time=stop_time,
				targeting=targeting,
				audience_network_positions=str(audience_network_positions),
				facebook_positions=str(facebook_positions),
				instagram_positions=str(instagram_positions),
				messenger_positions=str(messenger_positions),
				publisher_platforms=str(publisher_platforms),
				created_time=created_time,
				status=status
			)
			print(f"Inserted new ad set ith id: {meta_ad_set_id}")
	
		else:
			
			meta_ad_set = MetaAdSets.objects.filter(meta_ad_set_id=meta_ad_set_id).first()

			ad_set_id = ad_set_platform.ad_set_id
			print('Ad Set Exists!')
			# Update MetaAdSets entry
			meta_ad_set.name = name
			meta_ad_set.daily_budget = daily_budget
			meta_ad_set.daily_spend_cap = daily_spend_cap
			meta_ad_set.lifetime_budget = lifetime_budget
			meta_ad_set.start_time = start_time
			meta_ad_set.end_time = stop_time
			meta_ad_set.targeting = targeting
			meta_ad_set.publisher_platforms = str(publisher_platforms)
			meta_ad_set.status = status
			meta_ad_set.save()


			# Update AdManagerAdSets entry
			ad_set = AdSets.objects.filter(id=ad_set_id).first()
			ad_set.name = name
			ad_set.spend_limit = lifetime_budget
			ad_set.age_min = age_min
			ad_set.age_max = age_max
			ad_set.gender = gender
			ad_set.status = status
			ad_set.disabled = disabled
			ad_set.is_deleted = False
			ad_set.save()
			print(f"Updated ad_set with ad_set_id: {ad_set_id}")
		
		print('publisher_platforms', publisher_platforms)
		print('publisher_platforms_enabled', publisher_platforms_enabled)
		for publisher_platform in publisher_platforms:
			print('publisher_platform', publisher_platform)

			if publisher_platform in publisher_platforms_enabled:
				disabled = False
				status = status
			else:
				disabled = True
				status = 'PAUSED'

			print('AdSetsPlatforms - publisher_platform', publisher_platform)
			AdSetsPlatforms.objects.update_or_create(
				ad_set_id=ad_set_id,
				publisher_platform=publisher_platform,
				api_id=meta_ad_set_id,
				ad_platform='meta_ads',
				disabled=disabled,
				status=status,
			)


		if interests is not None:
			for interest in interests:
				meta_interest, _ = MetaInterests.objects.update_or_create(
					meta_interest_id=interest['id'],
					defaults={
						'name': interest['name'],					
					}
				)

				MetaAdSetsInterests.objects.update_or_create(
					metaadset=meta_ad_set,
					interest=meta_interest,
				)

				AdSetsKeywords.objects.update_or_create(
					ad_set=ad_set,
					keyword=interest['name'],
				)

		if cities is not None:
			for city in cities:
				MetaAdSetsCities.objects.update_or_create(
					metaadset=meta_ad_set,
					country=city['country'],
					distance_unit=city['distance_unit'],
					key=city['key'],
					name=city['name'],
					radius=city['radius'],
					region=city['region'],
					region_id=city['region_id'],
				)

				AdSetsLocations.objects.update_or_create(
					ad_set=ad_set,
					location=city['name'],
					radius=city['radius'],
					distance_unit=city['distance_unit'],
				)

		if countries is not None:
			for country in countries:
				MetaAdSetsCountries.objects.update_or_create(
					metaadset=meta_ad_set,
					country=country,
					
				)

				AdSetsLocations.objects.update_or_create(
					ad_set=ad_set,
					location=country,
				)


		if custom_locations is not None:
			for location in custom_locations:
				MetaAdSetsCustomLocations.objects.update_or_create(
					metaadset=meta_ad_set,
					country=location['country'],
					distance_unit=location['distance_unit'],
					latitude=location['latitude'],
					longitude=location['longitude'],
					primary_city_id=location['primary_city_id'],
					radius=location['radius'],
					region_id=location['region_id'],
				)

				AdSetsLocations.objects.update_or_create(
					ad_set=ad_set,
					distance_unit=location['distance_unit'],
					gps_lat=location['latitude'],
					gps_lng=location['longitude'],
					radius=location['radius'],
				)

		if locales is not None:
			print('locales', locales)
			for locale in locales:
				print('locale', locale)
				MetaAdSetsLocales.objects.update_or_create(
					metaadset=meta_ad_set,
					locale=locale,
				)

				AdSetsLanguages.objects.update_or_create(
					ad_set=ad_set,
					language=locale,
				)
		
		
		return ad_set_id
		
	except Exception as e:
		print("Error",e)
		traceback.print_exc()  # Print the traceback information
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		

def get_ads(account, account_id, user_id, access_token):

	print('get_ads')
	#https://developers.facebook.com/docs/marketing-api/reference/adgroup/
	
	limit = 1

	while True:
		try:
			#input('press enter to get_ads...')
			
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
			
			
			# Get today's date
			current_date = date.today()

			# Calculate the start date (2 years ago)
			start_date = current_date - timedelta(days=data_days)

			# Convert dates to string format for the API
			time_range = {
				'since': start_date.strftime('%Y-%m-%d'),
				'until': current_date.strftime('%Y-%m-%d'),
			}

			params = {
				'filtering': '[{"field":"ad.impressions","operator":"GREATER_THAN","value":0}]',
				'limit': limit,
				'time_range': time_range,
			}
			
			paramsx = {
				'date_preset': 'last_year',
				'limit': limit,
				}
			
			ads = account.get_ads(fields=fields, params=params)
			print('ads', ads)
			# Access the response headers get usage limit data
			headers = ads.headers()
			print(headers)
			print('get_ads')
			check_api_usage(headers, account_id)
			
			#input('ads loaded...enter to continue')
			while True:
				#print(ads)
				for ad in reversed(ads):
					#print(ad)
					ad_info = update_or_create_ad(ad, user_id, access_token, account_id)
					#print(ad_info)
					if ad_info is not None:
						ad_id = ad_info[0]
						meta_ad_id = ad_info[1]
						print('ad_id is ', ad_id, 'and meta_ad_id is ', meta_ad_id)
						
						get_ad_insights(ad_id, meta_ad_id, account_id)
					
					else:
						print('ad_info is None')
					
				# Retrieve the next page of ad sets
				if ads.load_next_page():
					continue
				else:
					break

		except facebook_business.exceptions.FacebookRequestError as fb_error:
			if fb_error.api_error_code() == 17 and fb_error.api_error_message() == "User request limit reached":
				# Handle this specific error
				print('error getting ads due to User request limit reached', fb_error)
				slack_alert_api_issue(str(fb_error)) # Send a slack alert for the API issue.
				print('pausing for ' + str(throttle_delay) + ' seconds due to request limit...')
				time.sleep(throttle_delay)  # Introduce a longer delay, as you're hitting rate limits
				continue
			else:
				# Handle other Facebook API errors
				print('error getting ads a ', fb_error)
				traceback.print_exc()  # Print the traceback information
				slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
				print('pausing for ' + str(throttle_delay) + ' seconds...')
				time.sleep(throttle_delay) # Introduce a delay
				continue

		except Exception as e:
			print('error getting ads b ', e)
			traceback.print_exc()  # Print the traceback information
			slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
			print('pausing for ' + str(throttle_delay) + ' seconds...')
			time.sleep(throttle_delay) # Introduce a delay
			continue
		break


def update_or_create_ad(ad, user_id, access_token, account_id):

	try:
		print('update or create ad')

		print('ad is', ad)
		meta_ad_id = ad.get('id')
		print('meta_ad_id is', meta_ad_id)

		meta_ad_set_id = ad.get('adset_id')

		name = ad.get('name')

		status = ad.get('status')
		disabled = status == 'PAUSED'

		effective_status = ad.get('effective_status')

		created_time = ad.get('created_time')

		updated_time = ad.get('updated_time')

		meta_creative_id = ad['creative'].get('id')

		print('meta_creative_id is', meta_creative_id)

		if meta_creative_id:
			creative = get_creative(meta_creative_id, access_token, account_id)
		else:
			creative = []

		#print(creative)

		print('\033[92mname is', name, '\033[0m')
		print('status is', status)

		body = creative.get('body') if 'body' in creative else None
		primary_text = body or creative.get('asset_feed_spec', {}).get('bodies', [{}])[0].get('text')

		title = creative.get('title') if 'title' in creative else creative.get('asset_feed_spec', {}).get('titles', [{}])[0].get('text')
		headline = title

		call_to_action = creative.get('call_to_action_type') or creative.get('asset_feed_spec', {}).get('call_to_action_types', [{}])[0] or creative.get('object_story_spec', {}).get('link_data', {}).get('call_to_action', {}).get('type') or creative.get('object_story_spec', {}).get('video_data', {}).get('call_to_action', {}).get('type')

		if call_to_action is None:
			print("\033[91mno call to action\033[0m")
		else:
			print('call_to_action is', call_to_action)

		actor_id = creative.get('actor_id')
		facebook_page_id = actor_id if actor_id else None
		if not actor_id:
			print("\033[91mno facebook_page_id\033[0m")

		instagram_actor_id = creative.get('instagram_actor_id')
		instagram_account_id = instagram_actor_id if instagram_actor_id else None
		if not instagram_actor_id:
			print("\033[91mno instagram_account_id\033[0m")

		video_id = creative.get('video_id')
		if video_id:
			api_url = f"https://graph.facebook.com/" + META_API_VERSION + "/{video_id}"
			params = {
				"access_token": access_token,
				"fields": "permalink_url"
			}
			response = requests.get(api_url, params=params)
			data = response.json()
			video_permalink_url = data.get("permalink_url")
			print("\033[95mvideo_permalink_url is", video_permalink_url, "\033[0m")
		else:
			video_permalink_url = None

		destination_url = None
		if 'object_url' in creative:
			object_url = creative['object_url']
			destination_url = object_url
		else:
			object_url = None
			
		if 'object_store_url' in creative:
			object_store_url = creative['object_store_url']
			if destination_url is None:
				destination_url = object_store_url
		else:
			object_store_url = None

		
		if 'object_story_spec' in creative and 'link_data' in creative['object_story_spec'] and 'link' in creative['object_story_spec']['link_data']:
			destination_url = creative['object_story_spec']['link_data']['link']
		elif 'object_story_spec' in creative and 'video_data' in creative['object_story_spec'] and 'call_to_action' in creative['object_story_spec']['video_data'] and 'value' in creative['object_story_spec']['video_data']['call_to_action'] and 'link' in creative['object_story_spec']['video_data']['call_to_action']['value']:
			destination_url = creative['object_story_spec']['video_data']['call_to_action']['value']['link']
		elif 'asset_feed_spec' in creative and 'link_urls' in creative['asset_feed_spec'] and 'website_url' in creative['asset_feed_spec']['link_urls'][0]:
			destination_url = creative['asset_feed_spec']['link_urls'][0]['website_url']
		elif 'instagram_permalink_url' in creative and destination_url is None:
			destination_url = creative['instagram_permalink_url']
		elif video_permalink_url is not None and destination_url is None:
			destination_url = 'https://www.facebook.com/' + video_permalink_url

		if destination_url is None and 'preview_shareable_link' in ad:
			destination_url = ad['preview_shareable_link']
		
		if 'asset_feed_spec' in creative and 'link_urls' in creative['asset_feed_spec']:
			link_urls = creative['asset_feed_spec']['link_urls']
			if 'display_url' in link_urls[0]:
				display_url = link_urls[0]['display_url']
			elif len(link_urls) > 1 and 'display_url' in link_urls[1]:
				display_url = link_urls[1]['display_url']
			else:
				display_url = None
		else:
			display_url = None

		description = None
		if 'object_story_spec' in creative and 'link_data' in creative['object_story_spec'] and 'description' in creative['object_story_spec']['link_data']:
			description = creative['object_story_spec']['link_data']['description']
		elif 'object_story_spec' in creative and 'link_data' in creative['object_story_spec'] and 'message' in creative['object_story_spec']['link_data']:
			description = creative['object_story_spec']['link_data']['message']			
		elif 'asset_feed_spec' in creative and 'bodies' in creative['asset_feed_spec'] and len(creative['asset_feed_spec']['bodies']) > 1 and 'text' in creative['asset_feed_spec']['bodies'][1]:
			description = creative['asset_feed_spec']['bodies'][1]['text']
		elif 'asset_feed_spec' in creative and 'descriptions' in creative['asset_feed_spec'] and len(creative['asset_feed_spec']['descriptions']) > 1:
			description = creative['asset_feed_spec']['descriptions'][1]['text']
			
		elif 'asset_feed_spec' in creative and 'descriptions' in creative['asset_feed_spec']:
			description = creative['asset_feed_spec']['descriptions'][0]['text']
		elif 'object_story_spec' in creative and 'video_data' in creative['object_story_spec'] and 'link_description' in creative['object_story_spec']['video_data']:
			description = creative['object_story_spec']['video_data']['link_description']
		elif 'asset_feed_spec' in creative and 'titles' in creative['asset_feed_spec'] and 'text' in creative['asset_feed_spec']['titles'][0]:
			description = creative['asset_feed_spec']['titles'][0]['text']


		if description is not None and primary_text is not None and len(description) > len(primary_text):
			description_orig = description
			description = primary_text
			primary_text = description_orig
		if description is None and headline is None and primary_text is not None:
			print('\033[92mprimary_text is', primary_text, '\033[0m')
		elif description is None:
			print('\033[92mprimary_text is', primary_text, '\033[0m')
			print('\033[92mheadline is', headline, '\033[0m')
			
		elif headline is None:
			description_orig = description
			description = headline
			headline = description_orig
			print('\033[92mprimary_text is', primary_text, '\033[0m')
			print('\033[92mheadline is', headline, '\033[0m')
		else:
			print('\033[92mprimary_text is', primary_text, '\033[0m')
			print('\033[92mheadline is', headline, '\033[0m')
			print('\033[92mdescription is', description, '\033[0m')

		if primary_text is None:
			print("\033[91mno primary text\033[0m")
			
		if headline	is None:
			print("\033[91mno headline \033[0m")
			
		if description is None:
			print("\033[91mno description\033[0m")
			
							
		if 'object_type' in creative:
			object_type = creative['object_type']
		else:
			object_type = None

		if destination_url is None:
			print("\033[91mno destination_url\033[0m")
		else:
			print('destination_url is', destination_url)

		if display_url is None and 'display_url' in str(creative):
			print("\033[95mmissing display_url EXISTS in creative\033[0m")
		else:
			print('display_url is', display_url)

		if 'image_url' in creative:
			image_url = creative['image_url']
			print('image_url is', image_url)
		else:
			image_url = None
			if 'image_url' in str(creative) and 'image_url' not in str(creative['object_story_spec']['video_data']):
				print("\033[95mmissing image_url EXISTS in creative\033[0m")
			else:
				print('no image_url')
			

		if 'thumbnail_url' in creative:
			thumbnail_url = creative['thumbnail_url']
			print('thumbnail_url is', thumbnail_url)		
		else:
			thumbnail_url = None
			if 'thumbnail_url' in str(creative):
				print("\033[95mmissing thumbnail_url EXISTS in creative\033[0m")
			else:
				print('no thumbnail_url')

	
		# this can be move into a function and called if ad is not skipped, otherwise we are making a lot of calls to the db
		def get_ad_set_campaign(meta_ad_set_id):
			try:

				# Fetch the Ad Set Data from the database
				ad_set_platforms = AdSetsPlatforms.objects.filter(
					ad_set__user_id=user_id,
					api_id=meta_ad_set_id,
					ad_platform='meta_ads'
				)

				# Check if any records are found
				if ad_set_platforms.exists():
					# Assuming all records have the same ad_set_id and campaign_id
					ad_set_id = ad_set_platforms.first().ad_set_id
					campaign_id = ad_set_platforms.first().ad_set.campaign_id

					# Compile a list of different publisher platforms
					publisher_platforms = [platform.publisher_platform for platform in ad_set_platforms]

					# Print the details
					print(f'Ad Set ID: {ad_set_id}, Campaign ID: {campaign_id}')
					print('Publisher Platforms:', publisher_platforms)
				else:
					print("\033[91mNo Ad Sets Platforms found\033[0m")
				
				# Return the attributes as a tuple
				return ad_set_id, campaign_id, publisher_platforms
			
			except ObjectDoesNotExist:
				# Log and handle the case where the MetaAdSet does not exist
				print(meta_ad_set_id)
				print("\033[91mno ad set . . .\033[0m")
				return None

		ads_platform = AdsPlatforms.objects.filter(
			ad__user_id=user_id,
			api_id=meta_ad_id, 
			ad_platform='meta_ads'
		).first()
		
		if ads_platform is None:
			print('no ad')
			# Ad does not exist, insert new entry
			
			ad_set_campaign = get_ad_set_campaign(meta_ad_set_id)
			ad_set_id = ad_set_campaign[0]
			campaign_id = ad_set_campaign[1]
			publisher_platforms = ad_set_campaign[2]
			#publisher_platforms = ast.literal_eval(publisher_platforms)

			new_ad = Ads.objects.create(
				user=user_id,
				campaign_id=campaign_id,
				ad_set_id=ad_set_id,
				name=name,
				destination_url=destination_url,
				display_url=display_url,
				headline=headline,
				primary_text=primary_text,
				description=description,
				call_to_action_meta=call_to_action,
				facebook_page=None,
				facebook_page_id=None,
				instagram_account=instagram_account_id,
				instagram_account_id=None,
				created=created_time,
				status=status,
				disabled=disabled,
				is_deleted=False
			)

			ad_id = new_ad.id

			print(f"New Ad ID is {ad_id}")
			
			new_meta_ad = MetaAds.objects.create(
				user=user_id,
				ad_id=ad_id,
				meta_ad_id=meta_ad_id,
				name=name,
				status=status,
				effective_status=effective_status,
				created_time=created_time,
				updated_time=updated_time,
				meta_creative_id=meta_creative_id,
				body=body,
				title=title,
				call_to_action=call_to_action,
				actor_id=actor_id,
				instagram_actor_id=instagram_actor_id,
				object_url=object_url,
				object_store_url=object_store_url,
				object_type=object_type,
				image_url=image_url,
				thumbnail_url=thumbnail_url,
				video_id=video_id
			)

			if image_url is not None:
				process_image(ad_id, image_url, user_id)

			if thumbnail_url is not None:
				process_thumb(ad_id, thumbnail_url)

			print(f"Inserted new ad with id: {new_meta_ad.meta_ad_id}")
			
		else:
			print('ad exists')
			ad_id = ads_platform.ad_id
			
			ad_set_campaign = get_ad_set_campaign(meta_ad_set_id)
			ad_set_id = ad_set_campaign[0]
			campaign_id = ad_set_campaign[1]
			publisher_platforms = ad_set_campaign[2]
			#publisher_platforms = ast.literal_eval(publisher_platforms)

			# Campaign already exists, update existing entry
			meta_ad = MetaAds.objects.filter(meta_ad_id=meta_ad_id).first()

			meta_ad.name = name
			meta_ad.status = status
			meta_ad.effective_status = effective_status
			meta_ad.created_time = created_time
			meta_ad.updated_time = updated_time
			meta_ad.meta_creative_id = meta_creative_id
			meta_ad.body = body
			meta_ad.title = title
			meta_ad.call_to_action = call_to_action
			meta_ad.actor_id = actor_id
			meta_ad.instagram_actor_id = instagram_actor_id
			meta_ad.object_url = object_url
			meta_ad.object_store_url = object_store_url
			meta_ad.object_type = object_type
			meta_ad.image_url = image_url
			meta_ad.thumbnail_url = thumbnail_url
			meta_ad.video_id = video_id
			meta_ad.save()
			print(f"Updated meta ad with meta_ad_id: {meta_ad_id}")

			ad = Ads.objects.get(id=ad_id)
			ad.name = name
			ad.destination_url = destination_url
			ad.display_url = display_url
			ad.headline = headline
			ad.primary_text = primary_text
			ad.description = description
			ad.call_to_action_meta = call_to_action
			ad.facebook_page = None
			ad.facebook_page_id = facebook_page_id
			ad.instagram_account = None
			ad.instagram_account_id = instagram_account_id
			ad.created = created_time
			ad.status = status
			ad.disabled = disabled
			ad.is_deleted = False
			ad.save()

			if image_url is not None and image_url != meta_ad.image_url:
				process_image(ad_id, image_url, user_id)

			if thumbnail_url is not None and thumbnail_url != meta_ad.thumbnail_url:
				process_thumb(ad_id, thumbnail_url)

			print(f"Updated ad with ad_id: {ad.id}")
		
		print(publisher_platforms)
		for publisher_platform in publisher_platforms:
						
			ad_platform_instance, created = AdsPlatforms.objects.get_or_create(
				ad_id=ad_id,
				publisher_platform=publisher_platform,
				api_id=meta_ad_id,
				ad_platform='meta_ads',		
			)
			'''
			ad_platform_instance, created = AdsPlatforms.objects.get_or_create(
				ad_id=ad_id,
				publisher_platform=publisher_platform,
				api_id=meta_ad_id,
				ad_platform='meta_ads',
				
				defaults={
					'ad_platform': 'meta_ads',
					'disabled': disabled,
					'status': status,
					'run_on': True,
					'disabled': False,
					'previously_disabled': False
				}
			)
			if not created:
				ad_platform_instance.disabled = disabled
				ad_platform_instance.status = status
				ad_platform_instance.run_on = True
				ad_platform_instance.save()'''
		
		return ad_id, meta_ad_id
		
	except Exception as e:
		print("Error",e)
		traceback.print_exc()  # Print the traceback information
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.


def get_creative(creative_id, access_token, account_id):

		#https://developers.facebook.com/docs/marketing-api/reference/ad-creative
	while True:
		try:

			print('start get_creative')
			
			fields = [
				'actor_id',
				'asset_feed_spec',
				'body',
				'bundle_folder_id',
				'call_to_action_type',
				'category_media_source',
				'dynamic_ad_voice',
				'effective_authorization_category',
				'effective_instagram_media_id',
				'effective_instagram_story_id',
				'effective_object_story_id',
				'image_url',
				'instagram_actor_id',
				'instagram_permalink_url',
				'instagram_story_id',
				'instagram_user_id',
				'interactive_components_spec',
				'link_destination_display_url',
				'link_og_id',
				'link_url',
				'messenger_sponsored_message',
				'name',
				'object_id',
				'object_store_url',
				'object_story_id',
				'object_story_spec',
				'object_type',
				'object_url',
				'place_page_set_id',
				'status',
				'template_url',
				'thumbnail_url',
				'title',
				'url_tags',
				'video_id'
			]
			params = {
				'thumbnail_width': 300,
				'thumbnail_height': 300,
				'access_token': access_token,
				'fields': ','.join(fields)
			}

			#creative = AdCreative(creative_id).api_get(fields=fields, params=params)
			#headers = creative.headers()
			#print(headers)
			# couldn't get headers so had to use requests
			url = f"https://graph.facebook.com/" + META_API_VERSION + "/{creative_id}/"
			print('url is', url)
			print('params are', params)
			response = requests.get(url, params=params)
			headers = response.headers
			print(headers)
			print('get_creative')
			
			check_api_usage(headers, account_id) # this doesn't work in v17.0 for creatives
			#response.raise_for_status()
			creative = response.json()
			print(creative)
			#input('...continue...')
			return creative
					
		except facebook_business.exceptions.FacebookRequestError as fb_error:
			if fb_error.api_error_code() == 17 and fb_error.api_error_message() == "User request limit reached":
				# Handle this specific error
				print('error getting ads due to User request limit reached', fb_error)
				slack_alert_api_issue(str(fb_error)) # Send a slack alert for the API issue.
				print('pausing for ' + str(throttle_delay) + ' seconds due to request limit...')
				time.sleep(throttle_delay)  # Introduce a longer delay, as you're hitting rate limits
				continue
			else:
				# Handle other Facebook API errors
				print('error getting ads a ', fb_error)
				traceback.print_exc()  # Print the traceback information
				slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
				print('pausing for ' + str(throttle_delay) + ' seconds...')
				time.sleep(throttle_delay) # Introduce a delay
				continue
		
		except Exception as e:
			print('error getting creative', e)
			traceback.print_exc()  # Print the traceback information
			slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
			print('pausing for ' + str(throttle_delay) + ' seconds...')
			time.sleep(throttle_delay) # Introduce a delay
			continue
		break


def process_image(ad_id, image_url, user_id):
	try:
		response = requests.get(image_url)
		img = Image.open(BytesIO(response.content))

		# Get image details
		width, height = img.size
		file_type = img.format
		file_name = urlparse(image_url).path.split('/')[-1]
		original_file_name = file_name
		mime_type = Image.MIME.get(file_type)  # Get MIME type
		print(mime_type)

		# Create a thumbnail
		thumbnail = img.copy()
		thumbnail.thumbnail((300, 300))

		# Generate a UUID for the thumbnail file name
		thumbnail_uuid = str(uuid.uuid4())
		thumbnail_file_name = f'thumbs/{thumbnail_uuid}{file_name[file_name.rfind("."):]}'

		display_file_name = f'{width}x{height}.{file_type.lower()}'
		# Save the image and thumbnail to S3
		with BytesIO() as output:
			thumbnail.save(output, format=file_type)
			output.seek(0)
			thumbnail_file = ContentFile(output.getvalue())
			actual_thumb_name = default_storage.save(thumbnail_file_name, thumbnail_file)

		with BytesIO() as output:
			img.save(output, format=file_type)
			output.seek(0)
			image_file = ContentFile(output.getvalue())
			actual_file_name = default_storage.save(f'media_files/{file_name}', image_file)

		#user = User.objects.get(user=user_id)
		media = Media(user=user_id, file=actual_file_name, file_type=file_type,original_file_name=original_file_name, display_file_name=display_file_name,
					  height=height, width=width, source='meta_ads',size=len(response.content))
		media.save()

		# Save the thumbnail file name to the 'thumbnail' column in ads_manager_ads table
		ad = Ads.objects.get(id=ad_id)
		ad.thumbnail = actual_thumb_name
		ad.save()

		print(width, height, file_type, file_name)
		
		return width, height, file_type, file_name
	except Exception as e:
		print("Error", e)
		traceback.print_exc()  # Print the traceback information
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
			

def process_thumb(ad_id, thumb_url):
	# we can get much larger images but we don't know the aspect ratio. Let's do something here to get the aspect ratio. We could download multiple sizes, analyze them, and see if we can download something good for the media library.
	try:
		response = requests.get(thumb_url)
		thumbnail = Image.open(BytesIO(response.content))

		file_type = thumbnail.format
	   
		mime_type = Image.MIME.get(file_type)  # Get MIME type
		print(mime_type)
   
		# Generate a UUID for the thumbnail file name
		thumbnail_uuid = str(uuid.uuid4())
		thumbnail_file_name = f'thumbs/{thumbnail_uuid}.{file_type}'

		# Save the image and thumbnail to S3
		with BytesIO() as output:
			thumbnail.save(output, format=file_type)
			output.seek(0)
			thumbnail_file = ContentFile(output.getvalue())
			actual_thumb_name = default_storage.save(thumbnail_file_name, thumbnail_file)
	   
		# Save the thumbnail file name to the 'thumbnail' column in ads_manager_ads table
		ad = Ads.objects.get(id=ad_id)
		ad.thumbnail = actual_thumb_name
		ad.save()

		print(actual_thumb_name)
		print('thumbnail created continue...')
		return actual_thumb_name
	except Exception as e:
		print("Error", e)
		traceback.print_exc()  # Print the traceback information
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		

def get_ad_insights(ad_id, meta_ad_id, account_id):

	# https://developers.facebook.com/docs/marketing-api/insights
	while True:	
		try:
			ad = Ad(meta_ad_id)	
			insights = ad.get_insights(params={'date_preset': 'maximum', 'time_increment': '1', 'breakdowns': ['publisher_platform']}, fields=['account_currency', 'attribution_setting', 'buying_type', 'clicks', 'conversion_rate_ranking', 'conversion_values', 'conversions', 'converted_product_quantity', 'cpc', 'cpm', 'date_start', 'full_view_impressions', 'full_view_reach', 'impressions', 'objective', 'optimization_goal', 'outbound_clicks', 'place_page_name', 'quality_ranking', 'reach', 'social_spend', 'spend', 'website_ctr'])
			
			print(insights.headers())
			headers = insights.headers()
			print(headers)
			print('get_ad_insights')
			check_api_usage(headers, account_id)
			#input('insights....continue')		
			#print(insights)
			
			for report in insights:
				print(report)
				#print('Wait 0.5s...')
				#time.sleep(0.5)
				#input('continue report')
				date_start = report.get('date_start')
				publisher_platform = report.get('publisher_platform')
				impressions = report.get('impressions', 0)
				clicks = report.get('clicks', 0)
				actions = report.get('actions')
				account_currency = report.get('account_currency')
				buying_type = report.get('buying_type')
				cost_per_action_type = str(report.get('cost_per_action_type'))
				cpc = report.get('cpc')
				cpm = report.get('cpm')
				cpp = report.get('cpp')
				ctr = report.get('ctr')
				objective = report.get('objective')
				optimization_goal = report.get('optimization_goal')
				outbound_clicks = str(report.get('outbound_clicks'))
				quality_ranking = report.get('quality_ranking')
				reach = report.get('reach')
				social_spend = report.get('social_spend')
				spend = report.get('spend')
				website_ctr = str(report.get('website_ctr'))

				meta_ad = MetaAds.objects.get(meta_ad_id=meta_ad_id).first

				metaadsperformance, _ = MetaAdsPerformance.objects.update_or_create(
					meta_ad=meta_ad,
					date=date_start,
					publisher_platform=publisher_platform,
					defaults={
						'impressions': impressions,
						'clicks': clicks,
						'actions': actions,

					}
				)

				#input('enered into db continue...')
				ad_performance, _ = AdsPerformance.objects.update_or_create(
					ad_id=ad_id,
					date=date_start,
					publisher_platform=publisher_platform,
					ad_platform='meta_ads',
					defaults={
						'impressions': impressions,
						'clicks': clicks,
						'actions': actions,
						'spend': spend,
					}
				)
				print(f"Updated ad reporting data for ad_id: {ad_id}")

		
				#input('continue')

		except facebook_business.exceptions.FacebookRequestError as fb_error:
			if fb_error.api_error_code() == 17 and fb_error.api_error_message() == "User request limit reached":
				# Handle this specific error
				print('error getting get_ad_insights due to User request limit reached', fb_error)
				slack_alert_api_issue(str(fb_error)) # Send a slack alert for the API issue.
				print('pausing for ' + str(throttle_delay) + ' seconds due to request limit...')
				time.sleep(throttle_delay)  # Introduce a longer delay, as you're hitting rate limits
				continue
			else:
				# Handle other Facebook API errors
				print('error getting ads a ', fb_error)
				traceback.print_exc()  # Print the traceback information
				slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
				print('pausing for ' + str(throttle_delay) + ' seconds...')
				time.sleep(throttle_delay) # Introduce a delay
				continue
		

		except Exception as e:
			print('get_ad_insights error', e)
			traceback.print_exc()  # Print the traceback information
			slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
			print('pausing for ' + throttle_delay + ' seconds...')
			time.sleep(throttle_delay) # Introduce a delay
			continue
		break
