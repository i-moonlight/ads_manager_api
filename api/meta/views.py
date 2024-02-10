from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin
from django.template import loader
import requests

from ..ad_accounts.models import Authorizations
from .models import *

from datetime import datetime
import os
import sys
import traceback
import uuid

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.exceptions import FacebookRequestError
from facebook_business.api import FacebookAdsApi
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django_q.models import OrmQ

from core.utils.slack import slack_alert_api_issue


META_SYSTEM_USER_ACCESS_TOKEN = getattr(settings, 'META_SYSTEM_USER_ACCESS_TOKEN')
META_APP_ID = getattr(settings, 'META_APP_ID')
META_APP_SECRET = getattr(settings, 'META_APP_SECRET')
META_APP_TOKEN  = getattr(settings, 'META_APP_TOKEN')
META_API_VERSION = getattr(settings, 'META_API_VERSION')

FacebookAdsApi.init(access_token=META_APP_TOKEN, app_secret=META_APP_SECRET, app_id=META_APP_ID)

class Enable(LoggingMixin, APIView):
	def get(self, request):
		Authorizations.objects.filter(
			user=request.user, ad_platform='meta_ads').delete()
		redirect_uri = getattr(settings, 'FE_SERVER') + '/ad-accounts'
		
		state = uuid.uuid4()
		state = str(state)

		print('meta_app_id', META_APP_ID)
		print('redirect_uri', redirect_uri)
		print('state', state)
		print('meta_api_version', META_API_VERSION)
		authorization_url = 'https://www.facebook.com/' + META_API_VERSION + '/dialog/oauth?client_id=' + META_APP_ID + '&redirect_uri=' + redirect_uri + '&scope=ads_management,pages_show_list&state=' + state
		
		return Response({"authorization_url": authorization_url})


class DisableAPI(LoggingMixin, APIView):
	def delete(self, request):
		print('disabled meta_ads')
		ad_platform = 'meta_ads'
		task_id = request.data.get('taskId')

		Authorizations.objects.filter(
			user=request.user, ad_platform=ad_platform).delete()

		Campaigns.objects.filter(
			user=request.user, 
			campaigns_platform__ad_platform=ad_platform, 
			campaigns_platform__api_id__isnull=False 
		).update(is_deleted=True)

		AdSets.objects.filter(
			user=request.user, 
			ad_sets_platform__ad_platform=ad_platform, 
			ad_sets_platform__api_id__isnull=False
		).update(is_deleted=True)

		Ads.objects.filter(
			user=request.user,
			ads_platform__ad_platform=ad_platform,
			ads_platform__api_id__isnull=False
		).update(is_deleted=True)


		if task_id:
			try:
				ormq = OrmQ.objects.get(id=task_id)
				ormq.delete()

				channel_layer = get_channel_layer()
				async_to_sync(channel_layer.group_send)('ad-accounts', {
					'type': 'send_notification',
					'ad_platform': ad_platform,
					'is_importing': False,
					'message': 'Import cancelled'
				})
			except OrmQ.DoesNotExist:
				pass

		return Response(status=status.HTTP_204_NO_CONTENT)

class Oauth(LoggingMixin, APIView):
	def post(self, request):
		try:
			code = request.data.get("code")
			code = str(code)
			print('meta oauth A')
			# Get Access token
			redirect_uri = getattr(settings, 'FE_SERVER') + '/ad-accounts'

			access_token_url = 'https://graph.facebook.com/' + META_API_VERSION + '/oauth/access_token?client_id=' + META_APP_ID + \
				'&redirect_uri=' + redirect_uri + '&client_secret=' + \
				META_APP_SECRET + '&code=' + code

			token_info = requests.get(access_token_url)
			token_info = token_info.json()
			access_token = token_info['access_token']

			fb_url_me = 'https://graph.facebook.com/me?fields=id,first_name,middle_name,last_name,name,email'
			headers_api = {
				'Authorization': 'Bearer ' + access_token
			}
			
			print('meta oauth B')

			data_me = requests.get(url=fb_url_me, headers=headers_api)
			print('meta oauth C')
			response_me = data_me._content.decode('utf-8')
			print('response_me', response_me)

			authorization = Authorizations()
			authorization.user = request.user
			authorization.ad_platform = 'meta_ads'
			authorization.access_token = access_token
			authorization.save()

			debug_token_url = 'https://graph.facebook.com/' + META_API_VERSION + '/debug_token?input_token=' + \
				access_token + '&access_token=' + META_APP_TOKEN

			print('meta oauth E')
			debug_token_info = requests.get(debug_token_url)
			print('meta oauth F')
			debug_token_info = debug_token_info.json()

			expires_at = debug_token_info['data']['expires_at']

			fb_user_id = debug_token_info['data']['user_id']

			authorization.platform_user_id = fb_user_id
			authorization.save()


			account_info_url = 'https://graph.facebook.com/' + META_API_VERSION + '/' + \
				str(fb_user_id) + '/assigned_ad_accounts?access_token=' + \
				META_SYSTEM_USER_ACCESS_TOKEN
			ad_account_info = requests.get(account_info_url)
			ad_account_info = ad_account_info.json()

			account_info_url = 'https://graph.facebook.com/' + META_API_VERSION + '/me/adaccounts?fields=name,business,account_id,currency,timezone_id&access_token=' + access_token

			account_info_url = 'https://graph.facebook.com/' + META_API_VERSION + '/me/adaccounts?fields=name,account_id,currency,timezone_id&access_token=' + access_token

			ad_account_info = requests.get(account_info_url)
			ad_account_info = ad_account_info.json()
			
			account_ids = ad_account_info['data']
			
			accounts = []
			for i in account_ids:
				account = {}
				account['account_id'] = i['account_id']
				account['account_name'] = i['name']
				if 'business' in i:
					account['business_id'] = i['business']['id']
				accounts.append(account)

			if len(account_ids) == 1:
			
				account_id = account_ids[0]['account_id']
				account_name = account_ids[0]['name']
				authorization.account_id = account_id
				authorization.account_name = account_name
				authorization.date_time = datetime.utcnow()
				authorization.save()
				
			return Response({'accounts': accounts, 'ad_platform': 'meta_ads'})
		except Exception as e:
			print("this is error",e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
			return Response({
				'status' : 'Error',
				'message': 'There was an error',
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Pages(LoggingMixin, APIView):
	def get(self,request,format=None):

		try:
			print('GET PAGES')
			authorization = Authorizations.objects.get(user=request.user,ad_platform='meta_ads')
			fb_user_id = authorization.platform_user_id
			access_token = authorization.access_token

			url = 'https://graph.facebook.com/' + META_API_VERSION + '/' + \
			str(fb_user_id) + '/accounts?access_token=' + \
			access_token
			accounts_data  = requests.get(url)
			accounts  = accounts_data.json()['data']
			#print(accounts)
			
			pages = []
			for account in accounts:
				page = {}
				page['name'] = account['name']
				page['id'] = account['id']

				pages.append(page)
			
			print(pages)
			return Response({"pages": pages})
		except Exception as e:
			traceback.print_exc()  # Print the traceback information
			slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
			return Response({
				'status' : 'Error',
				'message': 'There was an error',
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

	# def get(self,request,format=None):

	# 	try:
	# 		print('get Facebook Pages')
			
	# 		pages = [
	# 			{
	# 			"name": "Facebook Page Test A",
	# 			"id": "101387855401774"
	# 			},
	# 			{
	# 			"name": "Facebook Page Test B",
	# 			"id": "105794688551547"
	# 			},
	# 			{
	# 			"name": "Facebook Page Test C",
	# 			"id": "108324801697548"
	# 			},
	# 			{
	# 			"name": "Facebook Page Test D",
	# 			"id": "111308081671695"
	# 			},
	# 			{
	# 			"name": "Facebook Page Test E",
	# 			"id": "114234645367508"
	# 			},
				
	# 		]
			
	# 		return Response({"pages": pages})
	# 	except Exception as e:
	# 		print("this is error",e)
	# 		exc_type, exc_obj, exc_tb = sys.exc_info()
	# 		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	# 		fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
	# 		print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
	# 		return Response({
	# 			'status' : 'Error',
	# 			'message': 'There was an error',
	# 		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Accounts(LoggingMixin, APIView):
	def get(self,request,format=None):

		try:
			print('Get Accounts')
			authorization = Authorizations.objects.get(user=request.user,ad_platform='meta_ads')
			fb_user_id = authorization.platform_user_id
			access_token = authorization.access_token
			
			url = 'https://graph.facebook.com/' + META_API_VERSION + '/' + \
			str(fb_user_id) + '/accounts?fields=instagram_business_account{name}&access_token=' + \
			access_token
			accounts_data  = requests.get(url)
			accounts  = accounts_data.json()['data']
			print(accounts)
			
			ig_accounts = []
			for account in accounts:
				if 'instagram_business_account' in account:
					ig_account = {}
					ig_account['name'] = account['instagram_business_account']['name']
					ig_account['id'] = account['instagram_business_account']['id']

					ig_accounts.append(ig_account)
			
			print(ig_accounts)
			return Response({"accounts": ig_accounts})
		except Exception as e:
			print("this is error",e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
			return Response({
				'status' : 'Error',
				'message': 'There was an error',
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
		slack_alert_api_issue(error_message) # Send a slack alert for the API issue.


	except Exception as e:
		print(e)
		traceback.print_exc()  # Print the traceback information
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		
		


def edit_campaign(account, campaign_id, campaign_data):

	print('edit meta campaign')
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


def edit_ad_set(account, ad_set_id, ad_set_data):

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


def create_ad(account, account_id, ad_data, access_token, user_id):

	print('create meta ad')
	try:
		# https://developers.facebook.com/docs/marketing-api/reference/ad-creative

		image_hash = None
		video_id = None

		if 'image' in ad_data['media_type'] and not ad_data.get('image_hash'):
			image_hash = create_ad_image_from_aws_bucket(account, account_id, ad_data['media_file'], ad_data['media_type'], user_id)
		elif 'image' in ad_data['media_type'] :
			image_hash = ad_data.get('image_hash')
		elif 'video' in ad_data['media_type'] and not ad_data.get('video_id'):
			video_info= create_ad_video_from_aws_bucket(account, ad_data['media_file'], ad_data['media_type'], user_id)
			video_id = video_info['video_id']
			image_hash = video_info['image_hash']
		elif ad_data.get('video_id'):
			video_id = ad_data.get('video_id')
			image_hash = ad_data.get('image_hash')
	
		#input('image_hash is ' + str(image_hash) + ' press enter to continue')
		params = {
			'name': ad_data.get('name', 'New Ad'),
			'adset_id': ad_data.get('ad_set_id'),
			'status': ad_data.get('status', 'PAUSED'),
			'creative': {
				'object_story_spec': {
					'page_id': ad_data.get('page_id'),
					
				},
				'degrees_of_freedom_spec': {
					'creative_features_spec': {
						'standard_enhancements': {
							'enroll_status': 'OPT_IN'	
						}					
					}
				}
			},
			
		}

		call_to_action = None
		# https://developers.facebook.com/docs/marketing-api/reference/ad-creative-link-data-call-to-action-value/
		if ad_data.get('call_to_action'):
			call_to_action = {'value': {}}
			call_to_action['type'] = ad_data.get('call_to_action')
			if ad_data.get('link'):
				call_to_action['value']['link'] = ad_data.get('link')
			if ad_data.get('display_url'):
				call_to_action['value']['link_caption'] = ad_data.get('display_url')

		if 'image' in ad_data['media_type']:
			params['creative']['object_story_spec']['link_data'] = {}
			params['creative']['object_story_spec']['link_data']['image_hash'] = image_hash
			params['creative']['object_story_spec']['link_data']['link'] = ad_data.get('link')
			params['creative']['object_story_spec']['link_data']['message'] = ad_data.get('primary_text')
			if ad_data.get('description'):
				params['creative']['object_story_spec']['link_data']['description'] = ad_data.get('description')
			if ad_data.get('headline'):
				params['creative']['object_story_spec']['link_data']['name'] = ad_data.get('headline')

			if call_to_action is not None:
				params['creative']['object_story_spec']['link_data']['call_to_action'] = call_to_action

			

		elif video_id is not None:
			# https://developers.facebook.com/docs/marketing-api/reference/ad-creative-video-data/#fields
			params['creative']['object_story_spec']['video_data'] = {}
			params['creative']['object_story_spec']['video_data']['video_id'] = video_id
			params['creative']['object_story_spec']['video_data']['image_hash'] = image_hash
			params['creative']['object_story_spec']['video_data']['message'] = ad_data.get('primary_text')
			if ad_data.get('description'):
				params['creative']['object_story_spec']['video_data']['link_description'] = ad_data.get('description')
			if ad_data.get('headline'):
				params['creative']['object_story_spec']['video_data']['title'] = ad_data.get('headline')
						
			if call_to_action is not None:
				params['creative']['object_story_spec']['video_data']['call_to_action'] = call_to_action
			
		else:
			raise Exception('No image or video provided')
	
		#if ad_data.get('link'):
		#	params['creative']['object_story_spec']['object_url'] = ad_data.get('link')
			
		if ad_data.get('display_url'):
			params['creative']['object_story_spec']['link_destination_display_url'] = ad_data.get('display_url')
		
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
		
				
		ad = account.create_ad(fields=fields, params=params)
		
		ad_id = ad.get_id()
		print('Created ad with ID:', ad_id)

		print(ad)
		creative_id = ad.get('creative')['id']

		creative = get_creative(creative_id, access_token)
		print(creative)

		return ad_id
	
	except FacebookRequestError as e:
		# Handle Facebook API errors
		print(e)
		
		error_message = e.api_error_message()	
		error_code = e.api_error_code()
		error_subcode = e.api_error_subcode()
		error_type = e.api_error_type()
		print(f"Facebook API error occurred when creating new ad:")
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
		return None


def edit_ad(account, ad_id, ad_data):

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


def create_ad_image_from_aws_bucket(account, account_id, media_file, media_type, user_id):
	try:
		# Initialize AWS S3 client
		s3 = boto3.client('s3')
		
	
		# Generate a random string for the temporary image filename
		random_string = str(uuid.uuid4())[:8]  # Generate a random string of length 8

		# Determine the file extension based on the content type
		file_extension = '.' + media_type.split('/')[-1]

		media_type = media_type.split('/')[0]

		# Specify the path where you want to temporarily save the image
		temp_image_path = f'temp/{random_string}' + file_extension

		print(temp_image_path)
		print('media_file is ' + media_file)
		print('aws bucket is ' + AWS_STORAGE_BUCKET_NAME)
		#input('press enter to continue')
		
		# Download the image from the AWS bucket
		s3.download_file(AWS_STORAGE_BUCKET_NAME, media_file, temp_image_path)
		
		# Initialize Facebook Ads API
		#FacebookAdsApi.init(access_token=access_token)

		# Create Ad Image
		ad_image = AdImage(parent_id='act_' + str(account_id))
		ad_image[AdImage.Field.filename] = temp_image_path
		ad_image.remote_create()

		image_hash = ad_image[AdImage.Field.hash]

		print(ad_image)

		params = {
			'hashes': [image_hash,
			],
		}
		image_info = account.get_ad_images(params=params)
		print(image_info)
		
		image_id = image_info[0]['id']

		print('Created Ad Image with ID:', image_id, ' and Hash:', image_hash)

		# Save ad image details to the MetaAdsMedia table
		MetaAdsMedia.objects.create(
			user_id=user_id,
			meta_ad_image_id=image_id,
			hash=image_hash,
			name=ad_image[AdImage.Field.name],
		)

		# Remove the temporary image file
		os.remove(temp_image_path)

		return image_hash
	
	except FacebookRequestError as e:
		# Handle Facebook API errors
		print(e)
		error_message = e.api_error_message()
		error_code = e.api_error_code()
		error_subcode = e.api_error_subcode()
		error_type = e.api_error_type()
		print(f"Facebook API error occurred when creating new ad image:")
		print(f"Message: {error_message}")
		print(f"Error Code: {error_code}")
		print(f"Error Subcode: {error_subcode}")
		print(f"Error Type: {error_type}")
		# Add any additional error handling or logging as needed
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.

	except Exception as e:
		print(f"Error occurred when creating new ad image: {str(e)}")
		traceback.print_exc()  # Print the traceback information
		#slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		input('error...')
		return None
		

def create_ad_video_from_aws_bucket(account, media_file, media_type, user_id):
	try:
		# Initialize AWS S3 client
		s3 = boto3.client('s3')
		
	
		# Generate a random string for the temporary image filename
		random_string = str(uuid.uuid4())[:8]  # Generate a random string of length 8

		# Determine the file extension based on the content type
		file_extension = '.' + media_type.split('/')[-1]

		media_type = media_type.split('/')[0]

		# Create a temporary file to save the image
		with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
			temp_image_path = temp_file.name

		print(temp_image_path)
		print('media_file is ' + media_file)
		print('aws bucket is ' + AWS_STORAGE_BUCKET_NAME)
		#input('press enter to continue')
		
		# Download the image from the AWS bucket
		s3.download_file(AWS_STORAGE_BUCKET_NAME, media_file, temp_image_path)
		
		# Create Ad Video
		video = account.create_ad_video(
			fields=['id', 'title', 'description', 'embed_html', 'format', 'source', 'status', 'created_time', 'updated_time'],
			params={
				'file_url': 'http://' + AWS_STORAGE_BUCKET_NAME + '.s3.amazonaws.com/' + media_file,
				
			}
		)
		print(video)

		video_id = video.get_id()
		print(f"Uploaded video with ID: {video_id}")
		input('press enter to continue')
		# Save ad image details to the MetaAdsMedia table
		MetaAdsMedia.objects.create(
			user_id=user_id,
			meta_ad_video_id=video_id,
		)

		# Remove the temporary image file
		os.remove(temp_image_path)

		return video_id
	
	except FacebookRequestError as e:
		# Handle Facebook API errors
		print(e)
		error_message = e.api_error_message()
		error_code = e.api_error_code()
		error_subcode = e.api_error_subcode()
		error_type = e.api_error_type()
		print(f"Facebook API error occurred when creating new ad image:")
		print(f"Message: {error_message}")
		print(f"Error Code: {error_code}")
		print(f"Error Subcode: {error_subcode}")
		print(f"Error Type: {error_type}")
		# Add any additional error handling or logging as needed
		slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.

	except Exception as e:
		print(f"Error occurred when creating new ad image: {str(e)}")
		traceback.print_exc()  # Print the traceback information
		#slack_alert_api_issue(traceback.format_exc()) # Send a slack alert for the API issue.
		input('error...')
		return None
		

def get_creative(creative_id, access_token):

		#https://developers.facebook.com/docs/marketing-api/reference/ad-creative
	try:
		
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

		print(access_token)
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
		url = f"https://graph.facebook.com/{META_API_VERSION}/{creative_id}/"
		response = requests.get(url, params=params)
		#headers = response.headers
		#print(headers)
		#print('get_creative')
		#check_api_usage(headers)
		#response.raise_for_status()
		creative = response.json()

		#input('...continue...')
		return creative
	
	except Exception as e:
		print('error getting creative', e)
		traceback.print_exc()  # Print the traceback information
		input('error...')
		return False
