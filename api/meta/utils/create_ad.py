# -*- coding: utf-8 -*-
#!/usr/bin/env python
import traceback

from api.meta.models import *
from api.ad_accounts.models import Authorizations

from django.conf import settings
from django.core.management.base import BaseCommand

from decouple import config
import requests
import boto3
import uuid
import os
import tempfile

import json
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adimage import AdImage
from facebook_business.adobjects.adcreativelinkdata import AdCreativeLinkData
from facebook_business.adobjects.adcreativeobjectstoryspec import AdCreativeObjectStorySpec
from facebook_business.exceptions import FacebookRequestError

from core.utils.slack import slack_alert_api_issue


META_APP_ID = getattr(settings, 'META_APP_ID')
META_APP_SECRET = getattr(settings, 'META_APP_SECRET')
META_API_VERSION = getattr(settings, 'META_API_VERSION')

AWS_STORAGE_BUCKET_NAME = getattr(settings, 'AWS_STORAGE_BUCKET_NAME')
AWS_ACCESS_KEY_ID = getattr(settings, 'AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = getattr(settings, 'AWS_SECRET_ACCESS_KEY')

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

	#images = account.get_ad_videos(fields=['status', 'permalink_url', 'name', 'hash'])
	#images = account.get_ad_videos(fields=['status', 'permalink_url', 'image_url', 'hash'])
	#print(images)
	#input('press enter to continue')

	ad_data = {}
	ad_data['name'] = 'Test Ad B 30'
	ad_data['ad_set_id'] = 23858016660000568
	ad_data['page_id'] = 574337732633404
	ad_data['link'] = 'https://www.linkclicks.com'
	ad_data['display_url'] = 'display.linkclicks.com'
	ad_data['primary_text'] = 'New Ad Primary Text'
	ad_data['headline'] = 'NEW AD HEADLINE'
	ad_data['description'] = 'NEW AD DESCRIPTION'
	ad_data['call_to_action'] = 'SIGN_UP'
	
	ad_data['status'] = 'PAUSED'
	#ad_data['media_file'] = 'media_files/1920x1080_iLAJUI7.png'
	#ad_data['media_type'] = 'images/png'
	ad_data['image_hash'] = '60cd82e893da17851f2f9ac20464193a'
	ad_data['media_file'] = 'media_files/portrait_video_1080x1920_itA7yUP.mp4'
	ad_data['media_type'] = 'video/mp4'
	ad_data['video_id'] = '601243435489957'
	
	create_ad(account, account_id, ad_data, access_token, user_id)


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
