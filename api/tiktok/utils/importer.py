from django.db.models import Min
from api.ad_accounts.models import Authorizations
from datetime import timedelta, datetime
from api.ad_manager.models import Campaigns, CampaignsPlatforms, AdSets, AdSetsPlatforms, Ads, AdsPerformance, AdsPlatforms
import requests
import traceback
import json


adgroup_ids = []

def get_ads_min_created_date(brand_name, user):
	return Ads.objects.filter(user=user, brand_name=brand_name).aggregate(Min('ad_created_at'))['ad_created_at__min']


def get_ads_performance_data(integration_obj, user, start_date, end_date):
	min_created_date = get_ads_min_created_date('tiktok', user)
	if min_created_date is not None:
		start_date = min_created_date
	while start_date <= end_date:
		date = start_date.strftime('%Y-%m-%d')
		# here we should make a call to campaign api and get the performance data
		url = 'https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/'
		params = {
			'advertiser_id': integration_obj.account_id,
			'service_type': 'AUCTION',
			'report_type': 'BASIC',
			'data_level': 'AUCTION_AD',
			'dimensions': '["ad_id","stat_time_day"]',
			'metrics': '["ad_name","campaign_name","impressions","clicks", "spend", "adgroup_name","opt_status"]',
			'start_date': date,
			'end_date': date,
			'page_size': 1000,
			'page': 1,
			'filtering': f'[{{"field_name": "adgroup_ids", "filter_type": "IN", "filter_value": "{[int(json.loads(adgroup_id)) for adgroup_id in adgroup_ids]}"}}]'
		}
		headers = {
			'Access-Token': integration_obj.access_token,
			'Content-Type': 'application/json'
		}
		resp = requests.get(url, headers=headers, params=params)
		if resp.status_code == 200:
			resp = resp.json()['data']
			if resp['page_info']['total_number'] != 0:
				resp = resp['list'][0]
				campaign_obj = Campaigns.objects.filter(user=integration_obj.user, name=resp['metrics']['campaign_name']).first()
				ad_set_obj = AdSets.objects.filter(user=integration_obj.user, campaign__pk=campaign_obj.id, name=resp['metrics']['adgroup_name']).first()
				ad_obj = Ads.objects.filter(user=integration_obj.user, campaign__pk=campaign_obj.id, ad_set__pk=ad_set_obj.id, name=resp['metrics']['ad_name']).first()
				AdsPerformance.objects.get_or_create(
					ad=ad_obj,
					ad_platform='tiktok_ads',
					publisher_platform='tiktok',
					date=date,
					defaults={
						'impressions': resp['metrics']['impressions'],
						'clicks': int(resp['metrics']['clicks']),
						'spend': float(resp['metrics']['spend']),
						'status': resp['metrics']['opt_status']
					}
				)
				AdsPlatforms.objects.get_or_create(
					ad=ad_obj,
					ad_platform='tiktok_ads',
					publisher_platform='tiktok',
					api_id=resp['dimensions']['ad_id'],
					defaults={
						'status': resp['metrics']['opt_status']
					}
				)
		
		start_date += timedelta(days=1)


# def save_ads_data(integration_obj, campaign_obj, ad_set_obj, adgroup_id, date):
# 	# here we should make a call to campaign api and get the performance data
# 	url = 'https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/'
# 	params = {
# 		'advertiser_id': integration_obj.account_id,
# 		'service_type': 'AUCTION',
# 		'report_type': 'BASIC',
# 		'data_level': 'AUCTION_AD',
# 		'dimensions': '["ad_id"]',
# 		'metrics': '["ad_name","impressions","clicks", "spend", "adgroup_name", "budget", "opt_status", "call_to_action","ad_url","ad_profile_image","profile_image"]',
# 		'start_date': date,
# 		'end_date': date,
# 		'page_size': 1000,
# 		'page': 1,
# 		'filtering': f'[{{"field_name": "adgroup_ids", "filter_type": "IN", "filter_value": "[{adgroup_id}]"}}]'
# 	}
# 	headers = {
# 		'Access-Token': integration_obj.access_token,
# 		'Content-Type': 'application/json'
# 	}
# 	resp = requests.get(url, headers=headers, params=params)
# 	if resp.status_code == 200:
# 		resp = resp.json()['data']
# 		if resp['page_info']['total_number'] != 0:
# 			resp = resp['list'][0]
# 			ad_obj, _ = Ads.objects.get_or_create(
# 				user=integration_obj.user,
# 				campaign=campaign_obj,
# 				ad_set=ad_set_obj,
# 				name=resp['metrics']['ad_name'],
# 				defaults={
# 					'destination_url': resp['metrics']['ad_url'],
# 					'display_url': resp['metrics']['ad_profile_image'],
# 					'call_to_action_tiktok': resp['metrics']['call_to_action'],
# 					'status': resp['metrics']['opt_status']
# 				}
# 			)
# 			AdsPerformance.objects.get_or_create(
# 				ad=ad_obj,
# 				ad_platform='tiktok_ads',
# 				publisher_platform='tiktok',
# 				date=date,
# 				defaults={
# 					'impressions': resp['metrics']['impressions'],
# 					'clicks': int(resp['metrics']['clicks']),
# 					'spend': float(resp['metrics']['spend']),
# 					'status': resp['metrics']['opt_status']
# 				}
# 			)
# 			AdsPlatforms.objects.get_or_create(
# 				ad=ad_obj,
# 				ad_platform='tiktok_ads',
# 				publisher_platform='tiktok',
# 				api_id=resp['dimensions']['ad_id'],
# 				defaults={
# 					'status': resp['metrics']['opt_status']
# 				}
# 			)

# def save_adset_data(integration_obj, campaign_obj, campaign_id, start_date, end_date):
# 	# here we should make a call to campaign api and get the performance data
# 	url = 'https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/'
# 	while start_date <= end_date:
# 		date = start_date.strftime('%Y-%m-%d')
# 		params = {
# 			'advertiser_id': integration_obj.account_id,
# 			'service_type': 'AUCTION',
# 			'report_type': 'BASIC',
# 			'data_level': 'AUCTION_ADGROUP',
# 			'dimensions': '["adgroup_id"]',
# 			'metrics': '["spend", "adgroup_name", "budget", "opt_status"]',
# 			'start_date': date,
# 			'end_date': date,
# 			'page_size': 1000,
# 			'page': 1,
# 			'filtering': f'[{{"field_name":"campaign_ids","filter_type":"IN","filter_value":"[{campaign_id}]"}}]'
# 		}
# 		headers = {
# 			'Access-Token': integration_obj.access_token,
# 			'Content-Type': 'application/json'
# 		}
# 		resp = requests.get(url, headers=headers, params=params)
# 		if resp.status_code == 200:
# 			resp = resp.json()['data']
# 			if resp['page_info']['total_number'] != 0:
# 				resp = resp['list'][0]
# 				adset, _ = AdSets.objects.get_or_create(
# 					user=integration_obj.user,
# 					campaign=campaign_obj,
# 					name=resp['metrics']['adgroup_name'],
# 					defaults={
# 						'spend_limit': int(float(resp['metrics']['spend'])),
# 						'daily_budget': int(float(resp['metrics']['budget'])),
# 						'status': resp['metrics']['opt_status']
# 					}
# 				)
# 				AdSetsPlatforms.objects.get_or_create(
# 					ad_set=adset,
# 					ad_platform='tiktok_ads',
# 					publisher_platform='tiktok',
# 					api_id=resp['dimensions']['adgroup_id'],
# 					defaults={
# 						'status': resp['metrics']['opt_status']
# 					}
# 				)
# 				# we need to bring ad level data here
# 				save_ads_data(integration_obj, campaign_obj, adset, resp['dimensions']['adgroup_id'], date)
# 		# increment the start_date by 1 day
# 		start_date += timedelta(days=1)


def get_ads(integration_obj, start_date, end_date):
	try:
		url = 'https://business-api.tiktok.com/open_api/v1.3/ad/get/'
		page = 1
		params = {
			'advertiser_id': integration_obj.account_id,
			'page_size': 1000,
			'page': page,
			'fields': '["campaign_name","operation_status","adgroup_name","ad_name","create_time","ad_text","landing_page_url","profile_image_url"]',
			'filtering': f'{{"adgroup_ids": [{",".join(adgroup_ids)}],"creation_filter_start_time": "{start_date}", "creation_filter_end_time": "{end_date}"}}'
		}
		headers = {
			'Access-Token': integration_obj.access_token,
			'Content-Type': 'application/json'
		}
		resp = requests.get(url, headers=headers, params=params)
		ads_data = []
		if resp.status_code == 200:
			resp = resp.json()['data']
			if resp['page_info']['total_number'] != 0:
				ads_data = resp['list']
				# increment the page
				page += 1
				# get the total number of pages exists
				total_pages = resp['page_info']['total_page']
				while page <= total_pages:
					params['page'] = page
					resp = requests.get(url, headers=headers, params=params)
					if resp.status_code == 200:
						resp = resp.json()['data']
						if resp['page_info']['total_number'] != 0:
							ads_data += resp['list']
							# increment the page again
							page += 1
						else:
							break
					else:
						break
			else:
				print(f'Account id: {integration_obj.account_id} have no ads.')
		else:
			traceback.print_exc()
		
		return ads_data
	except:
		traceback.print_exc()
		return []


def save_ads(integration_obj, ads_list):
	for ad in ads_list:
		try:
			campaign_obj = Campaigns.objects.filter(user=integration_obj.user, name=ad['campaign_name']).first()
			ad_set_obj = AdSets.objects.filter(user=integration_obj.user, campaign__pk=campaign_obj.id, name=ad['adgroup_name']).first()
			Ads.objects.get_or_create(
				user=integration_obj.user,
				campaign=campaign_obj,
				ad_set=ad_set_obj,
				name=ad['ad_name'],
				defaults={
					'destination_url': ad['landing_page_url'],
					'display_url': ad['profile_image_url'],
					'primary_text': ad['ad_text'],
					'status': ad['operation_status'],
					'brand_name': 'tiktok',
					'ad_created_at': datetime.strptime(ad['create_time'].split(' ')[0], '%Y-%m-%d').date()
				}
			)
		except:
			traceback.print_exc()


def get_adgroups(integration_obj, start_date, end_date):
	try:
		url = 'https://business-api.tiktok.com/open_api/v1.3/adgroup/get/'
		page = 1
		params = {
			'advertiser_id': integration_obj.account_id,
			'page_size': 1000,
			'page': page,
			'fields': '["campaign_name","budget","adgroup_name","operation_status"]',
			'filtering': f'{{"creation_filter_start_time": "{start_date}", "creation_filter_end_time": "{end_date}"}}'
		}
		headers = {
			'Access-Token': integration_obj.access_token,
			'Content-Type': 'application/json'
		}
		resp = requests.get(url, headers=headers, params=params)
		adgroups_data = []
		if resp.status_code == 200:
			resp = resp.json()['data']
			if resp['page_info']['total_number'] != 0:
				adgroups_data = resp['list']
				# increment the page
				page += 1
				# get the total number of pages exists
				total_pages = resp['page_info']['total_page']
				while page <= total_pages:
					params['page'] = page
					resp = requests.get(url, headers=headers, params=params)
					if resp.status_code == 200:
						resp = resp.json()['data']
						if resp['page_info']['total_number'] != 0:
							adgroups_data += resp['list']
							# increment the page again
							page += 1
						else:
							break
					else:
						break
			else:
				print(f'Account id: {integration_obj.account_id} have no adgroups.')
		else:
			traceback.print_exc()
		
		return adgroups_data
	except:
		traceback.print_exc()
		return []


def save_adgroups(integration_obj, adgroups_list):
	for adgroup in adgroups_list:
		try:
			campaign_obj = Campaigns.objects.filter(user=integration_obj.user, name=adgroup['campaign_name']).first()
			adset, _ = AdSets.objects.get_or_create(
				user=integration_obj.user,
				campaign=campaign_obj,
				name=adgroup['adgroup_name'],
				defaults={
					'spend_limit': int(float(adgroup['budget'])),
					'status': adgroup['operation_status']
				}
			)
			AdSetsPlatforms.objects.get_or_create(
				ad_set=adset,
				ad_platform='tiktok_ads',
				publisher_platform='tiktok',
				api_id=adgroup['adgroup_id'],
				defaults={
					'status': adgroup['operation_status']
				}
			)
			# append a adgroup_id in global list of adgroup ids
			adgroup_ids.append(json.dumps(adgroup['adgroup_id']))
		except:
			traceback.print_exc()


def get_campaigns(integration_obj, start_date, end_date):
	try:
		url = 'https://business-api.tiktok.com/open_api/v1.3/campaign/get/'
		page = 1
		params = {
			'advertiser_id': integration_obj.account_id,
			'page_size': 1000,
			'page': page,
			'fields': '["campaign_name","budget","create_time","operation_status"]',
			'filtering': f'{{"creation_filter_start_time": "{start_date}", "creation_filter_end_time": "{end_date}"}}'
		}
		headers = {
			'Access-Token': integration_obj.access_token,
			'Content-Type': 'application/json'
		}
		resp = requests.get(url, headers=headers, params=params)
		campaign_data = []
		if resp.status_code == 200:
			resp = resp.json()['data']
			if resp['page_info']['total_number'] != 0:
				campaign_data = resp['list']
				# increment the page
				page += 1
				# get the total number of pages exists
				total_pages = resp['page_info']['total_page']
				while page <= total_pages:
					params['page'] = page
					resp = requests.get(url, headers=headers, params=params)
					if resp.status_code == 200:
						resp = resp.json()['data']
						if resp['page_info']['total_number'] != 0:
							campaign_data += resp['list']
							# increment the page again
							page += 1
						else:
							break
					else:
						break
			else:
				print(f'Account id: {integration_obj.account_id} have no campaigns.')
		else:
			traceback.print_exc()
		
		return campaign_data
	except:
		traceback.print_exc()
		return []

def save_campaigns(integration_obj, campaign_list):
	for campaign in campaign_list:
		try:
			campaign_obj, _ = Campaigns.objects.get_or_create(
				user=integration_obj.user,
				name=campaign['campaign_name'],
				defaults={
					'budget': campaign['budget'],
					'start_date': str(campaign['create_time']).split(' ')[0],
					'status': campaign['operation_status']
				}
			)
			if not CampaignsPlatforms.objects.filter(
				campaign__pk=campaign_obj.id,
				ad_platform='tiktok_ads',
				publisher_platform='tiktok',
				api_id=campaign['campaign_id'],
			).exists():
				CampaignsPlatforms.objects.create(
					campaign=campaign_obj,
					ad_platform='tiktok_ads',
					publisher_platform='tiktok',
					api_id=campaign['campaign_id'],
					status=campaign['operation_status']
				)
		except:
			traceback.print_exc()

def import_tiktok_account_data(account_id, user_id, start_date, end_date):
	print('IMPORT TIKTOK ACCOUNT DATA')
	try:
		authorization = Authorizations.objects.filter(user=user_id, account_id=account_id, ad_platform='tiktok').first()
		if authorization:
			# Import TikTok campaign Data
			campaigns = get_campaigns(authorization, start_date, end_date)
			if len(campaigns) > 0:
				save_campaigns(authorization, campaigns)
			# Import TikTok adgroup Data
			adgroups = get_adgroups(authorization, start_date, end_date)
			if len(adgroups) > 0:
				save_adgroups(authorization, adgroups)
			# Import TikTok ads Data
			ads = get_ads(authorization, start_date, end_date)
			if len(ads) > 0:
				save_ads(authorization, ads)
			# Import TikTok ads performance Data
			start_date = datetime.strptime(start_date.strftime('%Y-%m-%d'), '%Y-%m-%d').date()
			end_date = datetime.strptime(end_date.strftime('%Y-%m-%d'), '%Y-%m-%d').date()
			get_ads_performance_data(authorization, user_id, start_date, end_date)

			return {
				'message': 'TikTok Data Imported Successfully',
				'ad_platform': 'tiktok',
				'is_importing': False,
			}
		else:
			return {
				'message': 'Authorization not found for TikTok',
				'ad_platform': 'tiktok',
				'is_importing': False,
			}
			
	except Exception as e:
        # Handle any other exceptions here
		return {
          'message': f'Error: {str(e)}',
          'ad_platform': 'tiktok',
          'is_importing': False,
        }
