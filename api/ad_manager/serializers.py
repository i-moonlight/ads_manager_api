from rest_framework import serializers
from django.db import transaction
import json

from .models import *
from api.media_library.models import Media
from api.authentication.serializers.login import _get_user_id_from_token
from api.user.models import User

from django.db.models import Q, Sum, Min
from django.utils import timezone
from datetime import datetime

from core.utils.checkStatus import checkStatus

import sys
import os
from io import BytesIO
import uuid
from PIL import Image
import cv2
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from api.ad_accounts.models import Authorizations
from api.linkedin.utils.api import update_linkedin_campaign, update_linkedin_adset, update_linkedin_ad, update_linkedin_location
from django_q.tasks import async_task
from api.ad_manager.utils import send_notif


# Common =============================================

class UserSerializer(serializers.ModelSerializer):
	
	class Meta:
		model = User
		fields = '__all__'

class MediaSerializer(serializers.ModelSerializer):
	
	class Meta:
		model = Media
		fields = '__all__'

# Common End =========================================

# Campaign =============================================

class AdSetsKeywordsSerializer(serializers.ModelSerializer):
	
	class Meta:
		model = AdSetsKeywords
		fields = '__all__'

class AdSetsLanguagesSerializer(serializers.ModelSerializer):
	
	class Meta:
		model = AdSetsLanguages
		fields = '__all__'

class AdSetsLocationsSerializer(serializers.ModelSerializer):
	
	class Meta:
		model = AdSetsLocations
		fields = '__all__'

class AdSetsBasicSerializer(serializers.ModelSerializer):
	keywords_w_ad_set = serializers.SerializerMethodField(method_name="get_keywords_w_ad_set")
	languages_w_ad_set = serializers.SerializerMethodField(method_name="get_languages_w_ad_set")
	locations_w_ad_set = serializers.SerializerMethodField(method_name="get_locations_w_ad_set")
	
	class Meta:
		model = AdSets
		fields = '__all__'
	
	def get_keywords_w_ad_set(self, instance):
		queryset = instance.keywords_w_ad_set.filter()
		return AdSetsKeywordsSerializer(queryset,
								  many=True).data

	def get_languages_w_ad_set(self, instance):
		queryset = instance.languages_w_ad_set.filter()
		return AdSetsLanguagesSerializer(queryset,
								  many=True).data

	def get_locations_w_ad_set(self, instance):
		queryset = instance.locations_w_ad_set.filter()
		return AdSetsLocationsSerializer(queryset,
								  many=True).data

class CampaignsBasicSerializer(serializers.ModelSerializer):
	campaign_w_ad_sets = serializers.SerializerMethodField(method_name="get_campaign_w_ad_sets")

	class Meta:
		model = Campaigns
		fields = '__all__'

	def get_campaign_w_ad_sets(self, instance):
		queryset = instance.campaign_w_ad_sets.filter(is_deleted=False)
		return AdSetsBasicSerializer(queryset,
								  many=True).data

class LocationSerializer(serializers.ModelSerializer):
	ad_set = AdSetsBasicSerializer(required=False)     
	name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	radius = serializers.IntegerField(required=False)
	gps_lat = serializers.DecimalField(required=False, max_digits=9, decimal_places=6)
	gps_lng = serializers.DecimalField(required=False, max_digits=9, decimal_places=6)

	class Meta:
		model = AdSetsLocations
		fields = '__all__'

class AdSetsInCampaignSerializer(serializers.ModelSerializer):
	user = UserSerializer(required=False)
	campaign = CampaignsBasicSerializer(required=False)
	languages = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	locations = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	keywords = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	ad_set_id = serializers.IntegerField(required=False)

	class Meta:
		model = AdSets
		fields = '__all__'


class CampaignsPlatformsTempSerializer(serializers.ModelSerializer):
	class Meta:
		model = CampaignsPlatforms
		fields = '__all__'

class CampaignsBasicUnGroupSerializer(serializers.ModelSerializer):
	user = UserSerializer(required=False)
	campaigns_platform = serializers.SerializerMethodField(method_name="get_campaigns_platform")
	
	class Meta:
		model = Campaigns
		fields = '__all__'

	def get_campaigns_platform(self, instance):
		query = Q(campaign_id=instance.id)
		queryset = instance.campaigns_platform.filter(query)
		return CampaignsPlatformsTempSerializer(queryset, many=True).data


class CampaignsPlatformsSerializer(serializers.ModelSerializer):
	campaigns_performance = serializers.SerializerMethodField(method_name="get_campaigns_performance")
	
	run_on = serializers.SerializerMethodField()

	class Meta:
		model = CampaignsPlatforms
		fields = '__all__'

	def get_run_on(self, instance):
		# Retrieve related ads with run_on=True
		ads_run_on = AdsPlatforms.objects.filter(
			Q(ad__campaign=instance.campaign),
			Q(run_on=True),
			Q(publisher_platform=instance.publisher_platform)
		).exists()
		return ads_run_on
	
	def get_campaigns_performance(self, instance):
		publisher_platform = instance.publisher_platform
		ad_platform = instance.ad_platform
		campaign_id = instance.campaign.id

		if self.context:
			start_date = self.context.get('start_date')
			end_date = self.context.get('end_date')

			if start_date != 'null' and end_date != 'null':
				query = Q(ad__campaign_id=campaign_id, publisher_platform=publisher_platform, ad_platform=ad_platform, date__gte=start_date, date__lte=end_date)
			else:
				query = Q(ad__campaign_id=campaign_id, publisher_platform=publisher_platform, ad_platform=ad_platform)
			queryset = AdsPerformance.objects.filter(ad__campaign_id=campaign_id) \
							.values("ad_platform", "publisher_platform") \
							.annotate(
								id=Min('ad'),
								impressions=Sum('impressions'),
								clicks=Sum('clicks'),
								actions=Sum('actions'),
								spend=Sum('spend'),
								earned=Sum('earned')
							) \
							.filter(query)
			return AdsPerformanceSerializer(queryset, many=True).data


class CampaignsSerializer(serializers.ModelSerializer):
	campaigns_platform = serializers.SerializerMethodField(method_name="get_campaigns_platform")
	is_All_Paused = serializers.SerializerMethodField(method_name="get_is_All_Paused")
	is_Ad_Sets_Stopped = serializers.SerializerMethodField(method_name="get_is_Ad_Sets_Stopped")
	is_Ads_Paused = serializers.SerializerMethodField(method_name="get_is_Ads_Paused")
	campaigns_platform_strings = serializers.SerializerMethodField(method_name="get_campaigns_platform_strings")
	
	class Meta:
		model = Campaigns
		fields = '__all__'

	def get_is_All_Paused(self, instance):
		# start_date = self.context['start_date']
		# end_date = self.context['end_date']
		query = Q(campaign_id=instance.id, status="PAUSED")
		count_campaigns_platform_paused = instance.campaigns_platform.filter(query).count()
		# print("get_is_paused_{campaign_id}:", count_campaigns_platform_paused)
		query = Q(campaign_id=instance.id)
		count_campaigns_platform_not_paused = instance.campaigns_platform.filter(query).count()
		# print("get_is_not_paused_{campaign_id}:", count_campaigns_platform_not_paused)
		if count_campaigns_platform_paused == count_campaigns_platform_not_paused and count_campaigns_platform_not_paused > 0:
			return True
		return False
		
	def get_is_Ad_Sets_Stopped(self, instance):
		query = Q(campaign_id=instance.id, status="ACTIVE", is_deleted=0)
		count_ad_set_active = AdSets.objects.filter(query).count()
		# print("count_ad_set_active_{campaign_id}:", count_ad_set_active)
		if count_ad_set_active == 0:
			return True
		return False

	def get_is_Ads_Paused(self, instance):
		query = Q(campaign_id=instance.id, disabled=1, is_deleted=0)
		count_ads_paused = Ads.objects.filter(query).count()
		# print("count_ads_paused_{campaign_id}:", count_ads_paused)
		query = Q(campaign_id=instance.id, is_deleted=0)
		count_ads_not_paused = Ads.objects.filter(query).count()
		# print("count_ads_not_paused_{campaign_id}:", count_ads_not_paused)
		if count_ads_paused == count_ads_not_paused and count_ads_not_paused > 0:
			return True
		return False 
	
# ==========================================================

	def get_campaigns_platform(self, instance):
		start_date = self.context['start_date']
		end_date = self.context['end_date']
		# q0 = Ads.objects.filter(campaign_id=instance.id).count()
		# print("Count Ads: ", q0)
		# query0 = Q(campaign_id=instance.id, campaign__campaign_w_ads__isnull=False)
		# queryset1 = instance.campaigns_platform.filter(query0).distinct()
		# print("Count Ads: ", queryset1)
		query = Q(campaign_id=instance.id)
		queryset = instance.campaigns_platform.filter(query)
		context = {"campaign_id": instance.id, "start_date": start_date, "end_date": end_date}  
		# print("get_campaigns_platform: ", context)
		return CampaignsPlatformsSerializer(queryset, many=True, context=context).data
	
	def get_campaigns_platform_strings(self, instance):
		query = Q(campaign_id=instance.id)
		queryset = instance.campaigns_platform.filter(query).order_by('-publisher_platform')
		result = ''
		for item in queryset:
			publisher_platform = item.publisher_platform
			publisher_platform = publisher_platform.capitalize()
			result += publisher_platform + ','
		if len(result) > 0:
			result = result[:-1]
		return result
	
class CampaignsUpdateSerializer(serializers.ModelSerializer):
	id = serializers.IntegerField(required=False)
	user = UserSerializer(required=False)
	status = serializers.CharField(required=False)
	campaign_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
	campaign_platform_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
	
	destination_url = serializers.CharField(required=False)
	display_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	ad_set = AdSetsInCampaignSerializer(required=False)
	
	campaign_id = serializers.IntegerField(required=False)
	ad_set_id = serializers.IntegerField(required=False)
	budget = serializers.IntegerField(required=False, allow_null=True)
	daily_budget = serializers.IntegerField(required=False, allow_null=True)


	class Meta:
		model = Campaigns
		fields = '__all__'

	def changeStatusRunPause(self, request):        
		try:
			user_id = _get_user_id_from_token(request) 
			status = self.validated_data['status']        
			campaign_ids = self.validated_data.get('campaign_ids')
			disabled = self.validated_data['disabled']             
			campaign_platform_ids = self.validated_data.get('campaign_platform_ids')
			
			if campaign_ids:
				campaigns = Campaigns.objects.filter(user_id=user_id, id__in=campaign_ids)

				for c in campaigns:
					if status != 'PAUSED':
						total_spend = AdsPerformance.objects.filter(ad__campaign_id=c.id).aggregate(Sum('spend'))['spend__sum']
						total_spend_today = AdsPerformance.objects.filter(ad__campaign_id=c.id, date=timezone.now().date()).aggregate(Sum('spend'))['spend__sum']
						c.status = checkStatus(**{'start_date': c.start_date, 'end_date': c.end_date, 'total_spend': total_spend, 'total_spend_today': total_spend_today, 'budget': c.budget, 'daily_budget': c.daily_budget})
					else:
						c.status = status

					c.disabled = disabled
					c.save()

					for cp in c.campaigns_platform.all():
						if disabled:
							cp.status = status
							cp.previously_disabled = cp.disabled
							cp.disabled = disabled
						else:
							if not cp.previously_disabled:
								cp.status = cp.campaign.status 

							cp.disabled = cp.previously_disabled

						cp.save()

				return CampaignsBasicUnGroupSerializer(campaigns, many=True).data
			if campaign_platform_ids:
				campaign_platforms = CampaignsPlatforms.objects.filter(id__in=campaign_platform_ids)
				campaigns = set([cp.campaign for cp in campaign_platforms])

				if status != 'PAUSED':
					for c in campaigns:
						total_spend = AdsPerformance.objects.filter(ad__campaign_id=c.id).aggregate(Sum('spend'))['spend__sum']
						total_spend_today = AdsPerformance.objects.filter(ad__campaign_id=c.id, date=timezone.now().date()).aggregate(Sum('spend'))['spend__sum']

						c.status = checkStatus(**{'start_date': c.start_date, 'end_date': c.end_date, 'total_spend': total_spend, 'total_spend_today': total_spend_today, 'budget': c.budget, 'daily_budget': c.daily_budget})

						c.save()

				for cp in campaign_platforms:
					if status != 'PAUSED':
						cp.status = cp.campaign.status
					else:
						cp.status = status

					cp.disabled = disabled
					cp.save()

				for c in campaigns:
					if status == 'PAUSED':
						active_platforms = AdsPlatforms.objects.filter(ad__campaign_id=c.id, run_on=True, publisher_platform__in=[cp.publisher_platform for cp in c.campaigns_platform.exclude(status='PAUSED')]).exists()

						if not active_platforms:
							c.status = 'PAUSED'

					c.disabled = False
					c.save()

				return CampaignsBasicUnGroupSerializer(campaigns, many=True).data
		except Exception as error:
			print("CampaignsUpdateSerializer_changeStatusRunPause_error: ", error)
			return False

	def delete(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			campaign_ids = self.validated_data['campaign_ids']
			Campaigns.objects.filter(user_id=user_id, id__in=campaign_ids).update(is_deleted=True)
			AdSets.objects.filter(user_id=user_id, campaign_id__in=campaign_ids).update(is_deleted=True)  
			Ads.objects.filter(user_id=user_id, campaign_id__in=campaign_ids).update(is_deleted=True)           
			# Campaigns.objects.filter(user_id=user_id, id__in=campaign_ids).delete()
			return True
		except Exception as error:
			print("CampaignsUpdateSerializer_delete_error: ", error)
			return False

	def name_validate_update(self, request):
		id = self.validated_data['id']
		name = self.validated_data['name']
		filterExist = Campaigns.objects.filter(
			name=name).exclude(id=id)
		if len(filterExist) > 0:
			return False
		return True

	def update(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			id = self.validated_data['id']
			name = self.validated_data['name']
			budget = self.validated_data['budget']
			daily_budget = self.validated_data['daily_budget']
			start_date = self.validated_data['start_date']
			end_date = self.validated_data['end_date']
			credit = self.validated_data['credit']
			employment = self.validated_data['employment']
			housing = self.validated_data['housing']
			social = self.validated_data['social']          
			model = Campaigns.objects.get(user_id=user_id, id=id)
			model.name = name
			model.budget = budget
			model.daily_budget = daily_budget
			model.start_date = start_date
			model.end_date = end_date
			model.credit = credit
			model.employment = employment
			model.housing = housing
			model.social = social

			if model.status != 'PAUSED':
				total_spend = AdsPerformance.objects.filter(ad__campaign_id=model.id).aggregate(Sum('spend'))['spend__sum']
				total_spend_today = AdsPerformance.objects.filter(ad__campaign_id=model.id, date=timezone.now().date()).aggregate(Sum('spend'))['spend__sum']
				model.status = checkStatus(**{'start_date': start_date, 'end_date': end_date, 'total_spend': total_spend, 'total_spend_today': total_spend_today, 'budget': model.budget, 'daily_budget': model.daily_budget})

			model.save()

			try:
				linkedin_platform = model.campaigns_platform.get(ad_platform='linkedin')

				if linkedin_platform.api_id:
					start_str = start_date.strftime('%Y-%m-%d')
					end_str = end_date.strftime('%Y-%m-%d')
					start = int(datetime.strptime(start_str, '%Y-%m-%d').timestamp() * 1000)
					end = int(datetime.strptime(end_str, '%Y-%m-%d').timestamp() * 1000)

					new_campaign = {
							"name": name,
							"totalBudget": {
								"currencyCode": "USD",
								"amount": str(budget)
							},
							"status": 'ACTIVE' if model.status not in ['PAUSED','ACTIVE'] else model.status
						}

					if model.status == 'DRAFT':
						new_campaign['runSchedule'] = {"start": start, "end": end}

					access_token = Authorizations.objects.get(user_id=user_id, ad_platform='linkedin').access_token

					async_task(update_linkedin_campaign, access_token, linkedin_platform.api_id, new_campaign, hook=send_notif)
			except CampaignsPlatforms.DoesNotExist:
				pass

			model.campaigns_platform.exclude(status='PAUSED').update(status=model.status)

			return CampaignsBasicUnGroupSerializer(model).data
		except Exception as error:
			print("CampaignsUpdateSerializer_update_error: ", error)
			return False

	def name_validate_add(self, request):
		user_id = _get_user_id_from_token(request) 
		# user_id = 2 
		name = self.validated_data['name']
		filterExist = Campaigns.objects.filter(name=name, user_id=user_id)
		if len(filterExist) > 0:
			return False
		return True

	def add_with_draft_mode(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			name = self.validated_data['name']
			budget = self.validated_data['budget']
			daily_budget = self.validated_data['daily_budget']
			start_date = self.validated_data['start_date']
			end_date = self.validated_data['end_date']
			credit = self.validated_data['credit']
			employment = self.validated_data['employment']
			housing = self.validated_data['housing']
			social = self.validated_data['social']
			status = self.validated_data['status']
			# 
			destination_url = self.validated_data['destination_url']
			display_url = self.validated_data['display_url']
			# return             
			model_ad_set = None 
			model_campaign = Campaigns.objects.create(user_id=user_id, name=name, budget=budget, daily_budget=daily_budget, 
						start_date=start_date, end_date=end_date, credit=credit, employment=employment, housing=housing, social=social, status=status)
			if model_campaign:
				campaign_id = model_campaign.id
				ad_set = self.validated_data['ad_set']  
				name = ad_set['name']
				spend_limit = ad_set['spend_limit']
				age_min = ad_set['age_min']
				age_max = ad_set['age_max']
				gender = ad_set['gender']                
				languages = ad_set['languages']
				locations = ad_set['locations']
				keywords = ad_set['keywords']  
				status = ad_set['status']
				print("keywords: ", keywords)
				model_ad_set = AdSets.objects.create(campaign_id=campaign_id, user_id=user_id, name=name, spend_limit=spend_limit, age_min=age_min,
								age_max=age_max, gender=gender, status=status) 
				ad_set_id = model_ad_set.id
				try:
					if len(languages) > 0:
						languages = languages.split(';')
						print("add_with_draft_mode_languages: ", languages)
						for x in languages:
							AdSetsLanguages.objects.create(ad_set_id=ad_set_id, language=x)
				except Exception as error_language:
					print("CampaignsUpdateSerializer_add_with_draft_mode_language_error: ", error_language)
				try:
					locations_list = json.loads(locations)
					if len(locations_list) > 0:
						for x in locations_list:                            
							AdSetsLocations.objects.create(ad_set_id=ad_set_id, location=x['name'], radius=x['radius'], gps_lat=x['lat'], gps_lng=x['lng'])
					# if len(locations) > 0:
					#     locations = locations.split(';')
					#     print("add_with_draft_mode_locations: ", locations)
					#     for x in locations:
					#         if len(x) > 0:
					#             AdSetsLocations.objects.create(ad_set_id=ad_set_id, location=x)
				except Exception as error_location:
					print("CampaignsUpdateSerializer_add_with_draft_mode_location_error: ", error_location)
				try:
					if len(keywords) > 0:
						keywords = keywords.split(';')
						print("add_with_draft_mode_keywords: ", keywords)
						for x in keywords:
							if len(x) > 0:
								AdSetsKeywords.objects.create(ad_set_id=ad_set_id, keyword=x)
				except Exception as error_keyword:
					print("CampaignsUpdateSerializer_add_with_draft_mode_keyword_error: ", error_keyword)
				#
				#total_spend_campaign = CampaignsPerformance.objects.filter(campaign_id=campaign_id).aggregate(Sum('spend'))['spend__sum']
				# print("total_spend_campaign: ", total_spend_campaign)
				current_date = timezone.now().date()
				#total_spend_campaign_by_daily = CampaignsPerformance.objects.filter(campaign_id=campaign_id, date=current_date).aggregate(Sum('spend'))['spend__sum']
				#if total_spend_campaign is not None and total_spend_campaign_by_daily is not None and model_campaign.status != "PAUSED":
				#	if (total_spend_campaign >= budget and budget > 0) or (total_spend_campaign_by_daily >= daily_budget and daily_budget > 0):
				#		Campaigns.objects.filter(campaign_id=campaign_id).update(status="BUDGET MET")
				#
				# current_date = timezone.now().date()                
				# start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
				if model_campaign.start_date is not None:
					if model_campaign.start_date > current_date and model_campaign.status != "PAUSED":
						# print("model_campaign.start_date: ", model_campaign.start_date)
						Campaigns.objects.filter(id=campaign_id).update(status="SCHEDULED")                
				# end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
				if model_campaign.end_date is not None:
					if model_campaign.end_date < current_date and model_campaign.status != "PAUSED":
						Campaigns.objects.filter(id=campaign_id).update(status="COMPLETED") 
			data = {} 
			model_campaign_serializer = CampaignsBasicUnGroupSerializer(model_campaign)
			data['campaign'] = model_campaign_serializer.data
			model_ad_set_serializer = AdSetsTempSerializer(model_ad_set)
			data['ad_set'] = model_ad_set_serializer.data
			data['campaign_id'] = model_campaign.id
			data['ad_set_id'] = model_ad_set.id
			data['destination_url'] = destination_url
			data['display_url'] = display_url
			return data
		except Exception as error:
			print("CampaignsUpdateSerializer_add_with_draft_mode_error: ", error)
			return False

	def edit_with_draft_mode(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			name = self.validated_data['name']
			budget = self.validated_data['budget']
			daily_budget = self.validated_data['daily_budget']
			start_date = self.validated_data['start_date']
			end_date = self.validated_data['end_date']
			credit = self.validated_data['credit']
			employment = self.validated_data['employment']
			housing = self.validated_data['housing']
			social = self.validated_data['social']
			status = self.validated_data['status']
			# 
			destination_url = self.validated_data['destination_url']
			display_url = self.validated_data['display_url']
			ad_set = self.validated_data['ad_set']  
			#
			campaign_id = self.validated_data['campaign_id']
			#            
			Campaigns.objects.filter(id=campaign_id, user_id=user_id).update(name=name, budget=budget, daily_budget=daily_budget, 
						start_date=start_date, end_date=end_date, credit=credit, employment=employment, housing=housing, social=social, status=status) 
			model_campaign = Campaigns.objects.get(id=campaign_id, user_id=user_id)
			# 
			model_ad_set = None 
			if model_campaign:
				campaign_id = model_campaign.id
				ad_set = self.validated_data['ad_set']  
				name = ad_set['name']
				spend_limit = ad_set['spend_limit']
				age_min = ad_set['age_min']
				age_max = ad_set['age_max']
				gender = ad_set['gender']                
				languages = ad_set['languages']
				locations = ad_set['locations']
				keywords = ad_set['keywords']  
				status = ad_set['status']
				#
				ad_set_id = ad_set['ad_set_id']                
				AdSets.objects.filter(id=ad_set_id).update(campaign_id=campaign_id, user_id=user_id, name=name, spend_limit=spend_limit, age_min=age_min,
								age_max=age_max, gender=gender, status=status) 
				model_ad_set = AdSets.objects.get(id=ad_set_id)
				# 
				print("keywords: ", keywords)                
				try:
					if len(languages) > 0:
						languages = languages.split(';')
						print("edit_with_draft_mode_languages: ", languages)
						AdSetsLanguages.objects.filter(ad_set_id=ad_set_id).delete()
						for x in languages:
							AdSetsLanguages.objects.create(ad_set_id=ad_set_id, language=x)
				except Exception as error_language:
					print("CampaignsUpdateSerializer_edit_with_draft_mode_language_error: ", error_language)
				try:
					locations_list = json.loads(locations)
					if len(locations_list) > 0:
						AdSetsLocations.objects.filter(ad_set_id=ad_set_id).delete()
						for x in locations_list:                            
							AdSetsLocations.objects.create(ad_set_id=ad_set_id, location=x['name'], radius=x['radius'], gps_lat=x['lat'], gps_lng=x['lng'])
					# if len(locations) > 0:
					#     locations = locations.split(';')
					#     print("edit_with_draft_mode_locations: ", locations)
					#     AdSetsLocations.objects.filter(ad_set_id=ad_set_id).delete()
					#     for x in locations:
					#         if len(x) > 0:
					#             AdSetsLocations.objects.create(ad_set_id=ad_set_id, location=x)
				except Exception as error_location:
					print("CampaignsUpdateSerializer_edit_with_draft_mode_location_error: ", error_location)
				try:
					if len(keywords) > 0:
						keywords = keywords.split(';')
						print("edit_with_draft_mode_keywords: ", keywords)
						AdSetsKeywords.objects.filter(ad_set_id=ad_set_id).delete()
						for x in keywords:
							if len(x) > 0:
								AdSetsKeywords.objects.create(ad_set_id=ad_set_id, keyword=x)
				except Exception as error_keyword:
					print("CampaignsUpdateSerializer_edit_with_draft_mode_keyword_error: ", error_keyword)
				#
				#total_spend_campaign = CampaignsPerformance.objects.filter(campaign_id=campaign_id).aggregate(Sum('spend'))['spend__sum']
				current_date = timezone.now().date()
				#total_spend_campaign_by_daily = CampaignsPerformance.objects.filter(campaign_id=campaign_id, date=current_date).aggregate(Sum('spend'))['spend__sum']
				#if total_spend_campaign is not None and total_spend_campaign_by_daily is not None and model_campaign.status != "PAUSED":
				#	if (total_spend_campaign >= budget and budget > 0) or (total_spend_campaign_by_daily >= daily_budget and daily_budget > 0):
				#		Campaigns.objects.filter(campaign_id=campaign_id).update(status="BUDGET MET")
				# 
				current_date = timezone.now().date()
				if start_date is not None:
					# start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
					if start_date > current_date and model_campaign.status != "PAUSED":
						AdSets.objects.filter(id=ad_set_id).update(status="SCHEDULED")
				if end_date is not None:
					# end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
					if end_date < current_date and model_campaign.status != "PAUSED":
						AdSets.objects.filter(id=ad_set_id).update(status="COMPLETED")
				# 

			data = {} 
			model_campaign_serializer = CampaignsBasicSerializer(model_campaign)
			data['campaign'] = model_campaign_serializer.data
			model_ad_set_serializer = AdSetsBasicSerializer(model_ad_set)       
			data['ad_set'] = model_ad_set_serializer.data
			data['campaign_id'] = model_campaign.id
			data['ad_set_id'] = model_ad_set.id
			data['destination_url'] = destination_url
			data['display_url'] = display_url
			return data
		except Exception as error:
			print("CampaignsUpdateSerializer_edit_with_draft_mode_error: ", error)
			return False
		
	def changeStatusToPause(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2    
			status = self.validated_data['status']        
			campaign_id = self.validated_data['campaign_id']
			ad_set_id = self.validated_data['ad_set_id']             
			Campaigns.objects.filter(user_id=user_id, id=campaign_id).update(status=status, disabled=True)
			AdSets.objects.filter(user_id=user_id, id=ad_set_id).update(status=status, disabled=True)
			Ads.objects.filter(user_id=user_id, ad_set_id=ad_set_id).update(status=status, disabled=True)
			return True
		except Exception as error:
			print("CampaignsUpdateSerializer_changeStatusToPause_error: ", error)
			return False

	def changeStatusToRun(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2    
			status = self.validated_data['status']        
			campaign_id = self.validated_data['campaign_id']
			ad_set_id = self.validated_data['ad_set_id']             
			Campaigns.objects.filter(user_id=user_id, id=campaign_id).update(status=status, disabled=False)
			AdSets.objects.filter(user_id=user_id, id=ad_set_id).update(status=status, disabled=False)
			Ads.objects.filter(user_id=user_id, ad_set_id=ad_set_id).update(status=status, disabled=False)
			AdSetsPlatforms.objects.filter(ad_set_id=ad_set_id).update(status=status, disabled=False)
			AdsPlatforms.objects.filter(ad__ad_set_id=ad_set_id).update(status=status, disabled=False)
			return True
		except Exception as error:
			print("CampaignsUpdateSerializer_changeStatusToRun_error: ", error)
			return False

class CampaignsPlatformsUpdateSerializer(serializers.ModelSerializer):
	campaign = CampaignsBasicSerializer(required=False)
	campaign_platform_ids = serializers.CharField(required=False)
	
	class Meta:
		model = CampaignsPlatforms
		fields = '__all__'

	def changeStatusRunPause(self, request):
		try:
			# user_id = _get_user_id_from_token(request) 
			# user_id = 2    
			status = self.validated_data['status']        
			campaign_platform_ids = self.validated_data['campaign_platform_ids']
			campaign_platform_ids = campaign_platform_ids.split(',')  
			disabled = self.validated_data['disabled']             
			CampaignsPlatforms.objects.filter(id__in=campaign_platform_ids).update(status=status, disabled=disabled)
			return True
		except Exception as error:
			print("CampaignsPlatformsUpdateSerializer_changeStatusRunPause_error: ", error)
			return False

class CampaignsPlatformsUnGroupSerializer(serializers.ModelSerializer):
	campaigns_performance = serializers.SerializerMethodField(method_name="get_campaigns_performance")
	campaign_current = serializers.SerializerMethodField(method_name="get_campaign_current")
	run_on = serializers.SerializerMethodField()

	class Meta:
		model = CampaignsPlatforms
		fields = '__all__'

	def get_run_on(self, instance):
		# Retrieve related ads with run_on=True
		ads_run_on = AdsPlatforms.objects.filter(
			Q(ad__campaign=instance.campaign),
			Q(run_on=True),
			Q(publisher_platform=instance.publisher_platform)
		).exists()
		return ads_run_on
	
	def get_campaigns_performance(self, instance):
		publisher_platform = instance.publisher_platform
		ad_platform = instance.ad_platform
		campaign_id = instance.campaign_id

		if self.context:
			start_date = self.context.get('start_date')
			end_date = self.context.get('end_date')

			if start_date is not None and end_date is not None:
				query = Q(ad__campaign_id=campaign_id, publisher_platform=publisher_platform, ad_platform=ad_platform, date__gte=start_date, date__lte=end_date)
			else:
				query = Q(ad__campaign_id=campaign_id, publisher_platform=publisher_platform, ad_platform=ad_platform)
			queryset = AdsPerformance.objects.filter(ad__campaign_id=campaign_id) \
							.values("ad_platform", "publisher_platform") \
							.annotate(
								id=Min('ad__id'),
								impressions=Sum('impressions'),
								clicks=Sum('clicks'),
								actions=Sum('actions'),
								spend=Sum('spend'),
								earned=Sum('earned')
							) \
							.filter(query)
			return AdsPerformanceSerializer(queryset, many=True).data

	   
	def get_campaign_current(self, instance):
		campaign_id = instance.campaign_id
		queryset = Campaigns.objects.filter(id=campaign_id)
		return CampaignsBasicUnGroupSerializer(queryset,
								  many=True).data
	
	
# Campaign End =========================================

# AdSets =============================================
	
class AdSetsBasicUnGroupSerializer(serializers.ModelSerializer):
	user = UserSerializer(required=False)
	
	class Meta:
		model = AdSets
		fields = '__all__'

class AdSetsPlatformsSerializer(serializers.ModelSerializer):
	ad_sets_performance = serializers.SerializerMethodField(method_name="get_ad_sets_performance")
	run_on = serializers.SerializerMethodField()

	class Meta:
		model = AdSetsPlatforms
		fields = '__all__'

	def get_run_on(self, instance):
		ads_run_on = AdsPlatforms.objects.filter(
			Q(ad__ad_set=instance.ad_set),
			Q(run_on=True),
			Q(publisher_platform=instance.publisher_platform)
		).exists()
		return ads_run_on
	
	
	def get_ad_sets_performance(self, instance):
		publisher_platform = instance.publisher_platform
		ad_platform = instance.ad_platform
		ad_set_id = instance.ad_set.id

		if self.context:
			start_date = self.context.get('start_date')
			end_date = self.context.get('end_date')

			if start_date and end_date:
				query = Q(ad__ad_set_id=ad_set_id, publisher_platform=publisher_platform, ad_platform=ad_platform, date__gte=start_date, date__lte=end_date)
			else:
				query = Q(ad__ad_set_id=ad_set_id, publisher_platform=publisher_platform, ad_platform=ad_platform)
			queryset = AdsPerformance.objects.filter(ad__ad_set_id=ad_set_id) \
							.values("ad_platform", "publisher_platform") \
							.annotate(
								id=Min('ad'),
								impressions=Sum('impressions'),
								clicks=Sum('clicks'),
								actions=Sum('actions'),
								spend=Sum('spend'),
								earned=Sum('earned')
							) \
							.filter(query)
			return AdsPerformanceSerializer(queryset, many=True).data

class AdSetsSerializer(serializers.ModelSerializer):
	campaign = CampaignsBasicSerializer(required=False, many=False)
	languages_w_ad_set = serializers.SerializerMethodField(method_name="get_languages_w_ad_set")
	locations_w_ad_set = serializers.SerializerMethodField(method_name="get_locations_w_ad_set")
	keywords_w_ad_set = serializers.SerializerMethodField(method_name="get_keywords_w_ad_set")
	ad_sets_platform = serializers.SerializerMethodField(method_name="get_ad_sets_platform")
	ad_sets_platform_strings = serializers.SerializerMethodField(method_name="get_ad_sets_platform_strings")
	# 
	is_Ads_Paused = serializers.SerializerMethodField(method_name="get_is_Ads_Paused")
	is_Campaign_Paused = serializers.SerializerMethodField(method_name="get_is_Campaign_Paused")
	is_All_Paused = serializers.SerializerMethodField(method_name="get_is_All_Paused")
	is_Budget_Reached = serializers.SerializerMethodField(method_name="get_is_Budget_Reached")
	# is_Spend_Limit = serializers.SerializerMethodField(method_name="get_is_Spend_Limit")
	# is_Scheduled = serializers.SerializerMethodField(method_name="get_is_Scheduled")
	
	class Meta:
		model = AdSets
		fields = '__all__'

	def get_is_Ads_Paused(self, instance):
		query = Q(ad_set_id=instance.id, disabled=1, is_deleted=0)
		count_ads_paused = Ads.objects.filter(query).count()
		# print("count_ads_paused_{ad_set_id}:", count_ads_paused)
		query = Q(ad_set_id=instance.id, is_deleted=0)
		count_ads_not_paused = Ads.objects.filter(query).count()
		# print("count_ads_not_paused_{ad_set_id}:", count_ads_not_paused)
		# print("ad_set_id:", instance.id)
		if count_ads_paused == count_ads_not_paused and count_ads_not_paused > 0:
			return True
		return False
	
	def get_is_Campaign_Paused(self, instance):
		parent = instance.campaign
		if parent and parent.status == "PAUSED":                
			return True
		return False
	
	def get_is_All_Paused(self, instance):
		query = Q(ad_set_id=instance.id, status="PAUSED")
		query |= Q(ad_set_id=instance.id, status="ALL PAUSED")
		count_ad_sets_platform_paused = instance.ad_sets_platform.filter(query).count()
		# print("get_is_paused_{ad_set_id}:", count_ad_sets_platform_paused)
		query = Q(ad_set_id=instance.id)
		count_ad_sets_platform_not_paused = instance.ad_sets_platform.filter(query).count()
		# print("get_is_not_paused_{ad_set_id}:", count_ad_sets_platform_not_paused)
		if count_ad_sets_platform_paused == count_ad_sets_platform_not_paused and count_ad_sets_platform_not_paused > 0:
			return True
		return False
	
	def get_is_Budget_Reached(self, instance):
		parent = instance.campaign
		if parent and parent.status == "BUDGET MET":                
			return True
		return False

	# def get_is_Spend_Limit(self, instance):
	#     if instance.status == "SPEND LIMIT":                
	#         return True
	#     return False
	
	# def get_is_Scheduled(self, instance):
	#     if instance.status == "SCHEDULED":                
	#         return True
	#     return False
	
	# def get_is_Scheduled(self, instance):
	#     if instance.status == "SCHEDULED":                
	#         return True
	#     return False
	
# =======================================================
	
	def get_ad_sets_platform(self, instance):
		start_date = self.context['start_date']
		end_date = self.context['end_date']
		query = Q(ad_set_id=instance.id)
		queryset = instance.ad_sets_platform.filter(query)
		context = {"ad_set_id": instance.id, "start_date": start_date, "end_date": end_date}  
		# print("get_get_ad_sets_platform: ", context)
		return AdSetsPlatformsSerializer(queryset,
								  many=True, context=context).data
	
	def get_ad_sets_platform_strings(self, instance):
		query = Q(ad_set_id=instance.id)
		queryset = instance.ad_sets_platform.filter(query).order_by('-publisher_platform')
		result = ''
		for item in queryset:
			publisher_platform = item.publisher_platform
			publisher_platform = publisher_platform.capitalize()
			result += publisher_platform + ','
		if len(result) > 0:
			result = result[:-1]
		return result
	
	def get_languages_w_ad_set(self, instance):
		queryset = instance.languages_w_ad_set.filter()
		return AdSetsLanguagesSerializer(queryset,
								  many=True).data
	def get_locations_w_ad_set(self, instance):
		queryset = instance.locations_w_ad_set.filter()
		return AdSetsLocationsSerializer(queryset,
								  many=True).data

	def get_keywords_w_ad_set(self, instance):
		queryset = instance.keywords_w_ad_set.filter()
		return AdSetsKeywordsSerializer(queryset,
								  many=True).data

class AdSetsUpdateSerializer(serializers.ModelSerializer):
	id = serializers.IntegerField(required=False)
	user = UserSerializer(required=False)
	campaign = CampaignsBasicSerializer(required=False)
	status = serializers.CharField(required=False)
	ad_set_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
	languages = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	locations = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	keywords = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	campaign_id = serializers.IntegerField(required=False)
	destination_url = serializers.CharField(required=False)
	display_url = serializers.CharField(required=False, allow_null=True)
	ad_set_id = serializers.IntegerField(required=False)
	spend_limit = serializers.IntegerField(required=False, allow_null=True)

	class Meta:
		model = AdSets
		fields = '__all__'

	def changeStatusRunPause(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			status = self.validated_data['status']        
			ad_set_ids = self.validated_data['ad_set_ids']
			disabled = self.validated_data['disabled']             
			ad_sets = AdSets.objects.filter(user_id=user_id, id__in=ad_set_ids)

			for a in ad_sets:
				if status != 'PAUSED':
					total_spend = AdsPerformance.objects.filter(ad__ad_set_id=a.id).aggregate(Sum('spend'))['spend__sum']
					a.status = checkStatus(**{'total_spend': total_spend, 'budget': a.spend_limit})
				else:
					a.status = status

				a.disabled = disabled
				a.save()

				for asp in a.ad_sets_platform.all():
					if disabled:
						asp.status = status
						asp.previously_disabled = asp.disabled
						asp.disabled = disabled
					else:
						if not asp.previously_disabled:
							asp.status = asp.ad_set.status

						asp.disabled = asp.previously_disabled

					asp.save()

			for ad_set_id in ad_set_ids:
				'''
				try:
					model_ad_set = AdSets.objects.get(id=ad_set_id)
					spend_limit = model_ad_set.spend_limit
					if spend_limit is not None and spend_limit > 0:
						total_spend_ad_set = AdSetsPerformance.objects.filter(ad_set_id=ad_set_id).aggregate(Sum('spend'))['spend__sum']
						if total_spend_ad_set is not None and total_spend_ad_set >= spend_limit and model_ad_set.status != "PAUSED":
							model_ad_set.status = "SPEND LIMIT"
							model_ad_set.save()
				except Exception as err:
					pass      
				'''
			return AdSetsTempSerializer(ad_sets, many=True).data
		except Exception as error:
			print("AdSetsUpdateSerializer_changeStatusRunPause_error: ", error)
			return False

	def delete(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			ad_set_ids = self.validated_data['ad_set_ids']
			AdSets.objects.filter(user_id=user_id, id__in=ad_set_ids).update(is_deleted=True)  
			Ads.objects.filter(user_id=user_id, ad_set__in=ad_set_ids).update(is_deleted=True)  
			return True
		except Exception as error:
			print("AdSetsUpdateSerializer_delete_error: ", error)
			return False

	def update(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			ad_set_id = self.validated_data['id']
			name = self.validated_data['name']
			spend_limit = self.validated_data['spend_limit']
			daily_budget = self.validated_data['daily_budget']
			age_min = self.validated_data['age_min']
			age_max = self.validated_data['age_max']
			gender = self.validated_data['gender']
			languages = self.validated_data['languages']
			locations = self.validated_data['locations']
			keywords = self.validated_data['keywords']               
			model = AdSets.objects.get(user_id=user_id, id=ad_set_id)
			model.name = name
			model.spend_limit = spend_limit
			model.daily_budget = daily_budget
			model.age_min = age_min
			model.age_max = age_max
			model.gender = gender            

			status = model.status

			if model.status != 'PAUSED':
				total_spend = AdsPerformance.objects.filter(ad__ad_set_id=model.id).aggregate(Sum('spend'))['spend__sum']

				status = checkStatus(**{'total_spend': total_spend, 'budget': model.spend_limit})

				model.status = status

			model.save()

			try:
				linkedin_platform = model.ad_sets_platform.get(ad_platform='linkedin')

				if linkedin_platform.api_id:
					new_adset = {
						"name": name,
						"dailyBudget": {"amount": str(daily_budget)},
						"status": 'ACTIVE' if status not in ['PAUSED','ACTIVE'] else status
					}

					access_token = Authorizations.objects.get(user_id=user_id, ad_platform='linkedin').access_token

					async_task(update_linkedin_adset, access_token, linkedin_platform.api_id, new_adset, hook=send_notif)
			except AdSetsPlatforms.DoesNotExist:
				pass

			model.ad_sets_platform.exclude(status='PAUSED').update(status=model.status)

			# 
			# try:
			# 	'''
			# 	if spend_limit is not None:
			# 		total_spend_ad_set = AdSetsPerformance.objects.filter(ad_set_id=ad_set_id).aggregate(Sum('spend'))['spend__sum']
			# 		if total_spend_ad_set is not None and total_spend_ad_set >= spend_limit and model.status != "PAUSED":
			# 			model.status = "SPEND LIMIT"
			# 			model.save()
			# 	'''
			# 	model_campaign = model.campaign
			# 	current_date = timezone.now().date()
			# 	if model_campaign.start_date > current_date and model.status != "PAUSED":
			# 		model.status = "SCHEDULED"
			# 		model.save()
			# 	if model_campaign.end_date < current_date and model.status != "PAUSED":
			# 		model.status = "COMPLETED"
			# 		model.save()
			# except Exception as err_update_status:
			# 	print("AdSetsUpdateSerializer_update_status_error: ", err_update_status)
			# 
			try:
				languages = languages.split(';')
				print("languages: ", languages)
				AdSetsLanguages.objects.filter(ad_set_id=ad_set_id).delete()
				for x in languages:
					AdSetsLanguages.objects.create(ad_set_id=ad_set_id, language=x)
			except Exception as error_language:
				print("AdSetsUpdateSerializer_update_language_error: ", error_language)

			try:
				model.locations_w_ad_set.all().delete()

				location_names = []

				for l in json.loads(locations):
					model.locations_w_ad_set.create(location=l.get('name'), radius=l.get('radius'), gps_lat=l.get('lat'), gps_lng=l.get('lng'))

					location_names.append(l.get('name'))

				try:
					linkedin_platform = model.ad_sets_platform.get(ad_platform='linkedin')

					if linkedin_platform.api_id:
						access_token = Authorizations.objects.get(user_id=user_id, ad_platform='linkedin').access_token

						async_task(update_linkedin_location, access_token, linkedin_platform.api_id, location_names, hook=send_notif)
				except AdSetsPlatforms.DoesNotExist:
					pass

			except Exception as error_location:
				print("AdSetsUpdateSerializer_update_location_error: ", error_location)


			# try:
			# 	locations_list = json.loads(locations)
			# 	if len(locations_list) > 0:
			# 		AdSetsLocations.objects.filter(ad_set_id=ad_set_id).delete()
			# 		for x in locations_list:
			# 			AdSetsLocations.objects.create(ad_set_id=ad_set_id, location=x['name'], radius=x['radius'], gps_lat=x['lat'], gps_lng=x['lng'])
			# 	# locations = locations.split(';')
			# 	# print("locations: ", locations)
			# 	# AdSetsLocations.objects.filter(ad_set_id=ad_set_id).delete()
			# 	# for x in locations:
			# 	#     AdSetsLocations.objects.create(ad_set_id=ad_set_id, location=x)
			# except Exception as error_location:
			# 	print("AdSetsUpdateSerializer_update_location_error: ", error_location)
			try:
				keywords = keywords.split(';')
				print("keywords: ", keywords)
				AdSetsKeywords.objects.filter(ad_set_id=ad_set_id).delete()
				for x in keywords:
					AdSetsKeywords.objects.create(ad_set_id=ad_set_id, keyword=x)
			except Exception as error_keyword:
				print("AdSetsUpdateSerializer_update_keyword_error: ", error_keyword)
			return AdSetsTempSerializer(model).data
		except Exception as error:
			print("AdSetsUpdateSerializer_update_error: ", error)
			return False

	def add_from_campaign(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			campaign_id = self.validated_data['campaign_id'] 
			destination_url = self.validated_data['destination_url']
			display_url = self.validated_data['display_url']          
			name = self.validated_data['name']            
			age_min = self.validated_data['age_min']
			age_max = self.validated_data['age_max']
			gender = self.validated_data['gender']
			status = self.validated_data['status']  
			languages = self.validated_data['languages']
			locations = self.validated_data['locations']
			keywords = self.validated_data['keywords']               
			model_ad_set = AdSets.objects.create(user_id=user_id, campaign_id=campaign_id, name=name, spend_limit=0, age_min=age_min, age_max=age_max, gender=gender, status=status)
			model_ad_set.save()
			ad_set_id = model_ad_set.id
			# 
			try:
				model_campaign = model_ad_set.campaign
				current_date = timezone.now().date()
				if model_campaign.start_date > current_date:
					AdSets.objects.filter(id=ad_set_id).update(status="SCHEDULED")
				if model_campaign.end_date < current_date:
					AdSets.objects.filter(id=ad_set_id).update(status="COMPLETED")
			except Exception as err_update_status:
				print("AdSetsUpdateSerializer_add_from_campaign_err_update_status: ", err_update_status)
			# 
			try:
				if len(languages) > 0:
					languages = languages.split(';')
					print("languages: ", languages)
					AdSetsLanguages.objects.filter(ad_set_id=ad_set_id).delete()
					for x in languages:
						AdSetsLanguages.objects.create(ad_set_id=ad_set_id, language=x)
			except Exception as error_language:
				print("AdSetsUpdateSerializer_add_from_campaign_language_error: ", error_language)
			try:
				locations_list = json.loads(locations)
				if len(locations_list) > 0:
					AdSetsLocations.objects.filter(ad_set_id=ad_set_id).delete()
					for x in locations_list:                            
						AdSetsLocations.objects.create(ad_set_id=ad_set_id, location=x['name'], radius=x['radius'], gps_lat=x['lat'], gps_lng=x['lng'])
				# if len(locations) > 0:
				#     locations = locations.split(';')
				#     print("locations: ", locations)
				#     AdSetsLocations.objects.filter(ad_set_id=ad_set_id).delete()
				#     for x in locations:
				#         AdSetsLocations.objects.create(ad_set_id=ad_set_id, location=x)
			except Exception as error_location:
				print("AdSetsUpdateSerializer_add_from_campaign_location_error: ", error_location)
			try:
				if len(keywords) > 0:
					keywords = keywords.split(';')
					print("keywords: ", keywords)
					AdSetsLanguages.objects.filter(ad_set_id=ad_set_id).delete()
					for x in keywords:
						AdSetsKeywords.objects.create(ad_set_id=ad_set_id, keyword=x)
			except Exception as error_keyword:
				print("AdSetsUpdateSerializer_add_from_campaign_keyword_error: ", error_keyword)
			data = {}
			data['campaign_id'] = campaign_id
			data['ad_set_id'] = ad_set_id
			data['destination_url'] = destination_url
			data['display_url'] = display_url
			model_campaign = Campaigns.objects.get(id=campaign_id)
			model_campaign_serializer = CampaignsBasicSerializer(model_campaign)
			data['campaign'] = model_campaign_serializer.data
			# model_ad_set_serializer = AdSetsBasicSerializer(model_ad_set)
			model_ad_set_serializer = AdSetsTempSerializer(model_ad_set)
			data['ad_set'] = model_ad_set_serializer.data          
			return data
		except Exception as error:
			print("AdSetsUpdateSerializer_update_error: ", error)
			return False

	def updateExisting(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			ad_set_id = self.validated_data['ad_set_id']
			campaign_id = self.validated_data['campaign_id']
			destination_url = self.validated_data['destination_url']
			display_url = self.validated_data['display_url']
			name = self.validated_data['name']
			age_min = self.validated_data['age_min']
			age_max = self.validated_data['age_max']
			gender = self.validated_data['gender']
			languages = self.validated_data['languages']
			locations = self.validated_data['locations']
			keywords = self.validated_data['keywords']               
			model_ad_set = AdSets.objects.get(user_id=user_id, id=ad_set_id)
			model_ad_set.name = name
			model_ad_set.age_min = age_min
			model_ad_set.age_max = age_max
			model_ad_set.gender = gender            
			model_ad_set.save()
			try:
				if len(languages) > 0:
					languages = languages.split(';')
					print("languages: ", languages)
					AdSetsLanguages.objects.filter(ad_set_id=ad_set_id).delete()
					for x in languages:
						AdSetsLanguages.objects.create(ad_set_id=ad_set_id, language=x)
			except Exception as error_language:
				print("AdSetsUpdateSerializer_update_existing_language_error: ", error_language)
			try:
				locations_list = json.loads(locations)
				if len(locations_list) > 0:
					AdSetsLocations.objects.filter(ad_set_id=ad_set_id).delete()
					for x in locations_list:                            
						AdSetsLocations.objects.create(ad_set_id=ad_set_id, location=x['name'], radius=x['radius'], gps_lat=x['lat'], gps_lng=x['lng'])
				# if len(locations) > 0:
				#     locations = locations.split(';')
				#     print("locations: ", locations)
				#     AdSetsLocations.objects.filter(ad_set_id=ad_set_id).delete()
				#     for x in locations:
				#         AdSetsLocations.objects.create(ad_set_id=ad_set_id, location=x)
			except Exception as error_location:
				print("AdSetsUpdateSerializer_update_existing_location_error: ", error_location)
			try:
				if len(keywords) > 0:
					keywords = keywords.split(';')
					print("keywords: ", keywords)
					AdSetsKeywords.objects.filter(ad_set_id=ad_set_id).delete()
					for x in keywords:
						AdSetsKeywords.objects.create(ad_set_id=ad_set_id, keyword=x)
			except Exception as error_keyword:
				print("AdSetsUpdateSerializer_update_existing_keyword_error: ", error_keyword)
			data = {}
			data['campaign_id'] = campaign_id
			data['ad_set_id'] = ad_set_id
			data['destination_url'] = destination_url
			data['display_url'] = display_url
			model_campaign = Campaigns.objects.get(id=campaign_id)
			model_campaign_serializer = CampaignsBasicSerializer(model_campaign)
			data['campaign'] = model_campaign_serializer.data
			model_ad_set_serializer = AdSetsBasicSerializer(model_ad_set)       
			data['ad_set'] = model_ad_set_serializer.data          
			return data
		except Exception as error:
			print("AdSetsUpdateSerializer_update_existing_error: ", error)
			return False

class AdSetsPlatformsUpdateSerializer(serializers.ModelSerializer):
	ad_set = AdSetsBasicSerializer(required=False)
	ad_set_platform_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
	
	class Meta:
		model = AdSetsPlatforms
		fields = '__all__'

	def changeStatusRunPause(self, request):
		try:
			status = self.validated_data['status']        
			ad_set_platform_ids = self.validated_data['ad_set_platform_ids']
			disabled = self.validated_data['disabled']             

			ad_set_platforms = AdSetsPlatforms.objects.filter(id__in=ad_set_platform_ids)
			ad_sets = set([asp.ad_set for asp in ad_set_platforms])

			if status != 'PAUSED':
				for ad_set in ad_sets:
					total_spend = AdsPerformance.objects.filter(ad__ad_set_id=ad_set.id).aggregate(Sum('spend'))['spend__sum']
					ad_set.status = checkStatus(**{'total_spend': total_spend, 'budget': ad_set.spend_limit})
					ad_set.save()

			for asp in ad_set_platforms:
				if status != 'PAUSED':
					asp.status = asp.ad_set.status
				else:
					asp.status = status

				asp.disabled = disabled
				asp.save()

			for ad_set in ad_sets:
				if status == 'PAUSED':
					active_platforms = AdsPlatforms.objects.filter(ad__ad_set_id=ad_set.id, run_on=True, publisher_platform__in=[adp.publisher_platform for adp in ad_set.ad_sets_platform.exclude(status='PAUSED')]).exists()

					if not active_platforms:
						ad_set.status = 'PAUSED'

				ad_set.disabled = False
				ad_set.save()

			return AdSetsTempSerializer(ad_sets, many=True).data
		except Exception as error:
			print("AdSetsPlatformsUpdateSerializer_changeStatusRunPause_error: ", error)
			return False

class AdSetsPlatformsUnGroupSerializer(serializers.ModelSerializer):
	ad_sets_performance = serializers.SerializerMethodField(method_name="get_ad_sets_performance")
	ad_set_current = serializers.SerializerMethodField(method_name="get_ad_set_current")
	run_on = serializers.SerializerMethodField()
	
	class Meta:
		model = AdSetsPlatforms
		fields = '__all__'

	def get_run_on(self, instance):
		# Retrieve related ads with run_on=True
		ads_run_on = AdsPlatforms.objects.filter(
			Q(ad__ad_set=instance.ad_set),
			Q(run_on=True),
			Q(publisher_platform=instance.publisher_platform)
		).exists()
		return ads_run_on
	

	def get_ad_sets_performance(self, instance):
		publisher_platform = instance.publisher_platform
		ad_platform = instance.ad_platform
		ad_set_id = instance.ad_set_id

		if self.context:
			start_date = self.context.get('start_date')
			end_date = self.context.get('end_date')

			if start_date is not None and end_date is not None:
				query = Q(ad__ad_set_id=ad_set_id, publisher_platform=publisher_platform, ad_platform=ad_platform, date__gte=start_date, date__lte=end_date)
			else:
				query = Q(ad__ad_set_id=ad_set_id, publisher_platform=publisher_platform, ad_platform=ad_platform)
			queryset = AdsPerformance.objects.filter(ad__ad_set_id=ad_set_id) \
							.values("ad_platform", "publisher_platform") \
							.annotate(
								id=Min('ad__id'),
								impressions=Sum('impressions'),
								clicks=Sum('clicks'),
								actions=Sum('actions'),
								spend=Sum('spend'),
								earned=Sum('earned')
							) \
							.filter(query)
			return AdsPerformanceSerializer(queryset, many=True).data
   
	def get_ad_set_current(self, instance):
		ad_set_id = instance.ad_set_id
		queryset = AdSets.objects.filter(id=ad_set_id)
		return AdSetsBasicUnGroupSerializer(queryset,
								  many=True).data
		  
# AdSets End =========================================

# Ads =============================================

class AdsPlatformsBasicSerializer(serializers.ModelSerializer):
	class Meta:
		model = AdsPlatforms
		fields = '__all__'

class AdsBasicSerializer(serializers.ModelSerializer):
	media = MediaSerializer(required=False, many=False)
	ads_platform_strings = serializers.SerializerMethodField(method_name="get_ads_platform_strings")
	ads_platform = serializers.SerializerMethodField(method_name="get_ads_platform")

	class Meta:
		model = Ads
		fields = '__all__'

	def get_ads_platform_strings(self, instance):
		query = Q(ad_id=instance.id)
		queryset = instance.ads_platform.filter(query).order_by('-publisher_platform')
		result = ''
		for item in queryset:
			publisher_platform = item.publisher_platform
			publisher_platform = publisher_platform.capitalize()
			result += publisher_platform + ','
		if len(result) > 0:
			result = result[:-1]
		return result
	
	def get_ads_platform(self, instance):
		query = Q(ad_id=instance.id)
		queryset = instance.ads_platform.filter(query)
		return AdsPlatformsBasicSerializer(queryset,
								  many=True).data

class AdsSerializer(serializers.ModelSerializer):
	media = MediaSerializer(required=False, many=False)
	campaign = CampaignsBasicSerializer(required=False, many=False)
	ad_set = AdSetsBasicSerializer(required=False, many=False)
	ads_performance = serializers.SerializerMethodField(method_name="get_ads_performance")
	ads_platform = serializers.SerializerMethodField(method_name="get_ads_platform")
	# 
	is_Ad_Set_Paused = serializers.SerializerMethodField(method_name="get_is_Ad_Set_Paused")
	is_Campaign_Paused = serializers.SerializerMethodField(method_name="get_is_Campaign_Paused")
	is_All_Paused = serializers.SerializerMethodField(method_name="get_is_All_Paused")
	is_Budget_Reached = serializers.SerializerMethodField(method_name="get_is_Budget_Reached")
	is_Spend_Limit = serializers.SerializerMethodField(method_name="get_is_Spend_Limit")
	is_Scheduled = serializers.SerializerMethodField(method_name="get_is_Scheduled")
	is_Completed = serializers.SerializerMethodField(method_name="get_is_Completed")
	# 
	ads_platform_strings = serializers.SerializerMethodField(method_name="get_ads_platform_strings")

	class Meta:
		model = Ads
		fields = '__all__'

	def get_is_Ad_Set_Paused(self, instance):
		parent = instance.ad_set
		if parent and parent.status == "PAUSED":                
			return True
		return False
	
	def get_is_Campaign_Paused(self, instance):
		parent = instance.campaign
		if parent and parent.status == "PAUSED":                
			return True
		return False
	
	def get_is_All_Paused(self, instance):
		query = Q(ad_id=instance.id, status="PAUSED")
		count_ads_platform_paused = instance.ads_platform.filter(query).count()
		# print("get_is_paused_{ad_id}:", count_ads_platform_paused)
		query = Q(ad_id=instance.id)
		count_ads_platform_not_paused = instance.ads_platform.filter(query).count()
		# print("get_is_not_paused_{ad_id}:", count_ads_platform_not_paused)
		if count_ads_platform_paused == count_ads_platform_not_paused and count_ads_platform_not_paused > 0:
			return True
		return False
	
	def get_is_Budget_Reached(self, instance):
		parent = instance.campaign
		if parent and parent.status == "BUDGET MET":                
			return True
		return False
	
	def get_is_Spend_Limit(self, instance):
		parent = instance.ad_set
		if parent and parent.status == "SPEND LIMIT":                
			return True
		return False
	
	def get_is_Scheduled(self, instance):
		parent = instance.ad_set
		if parent and parent.status == "SCHEDULED":                
			return True
		return False
	
	def get_is_Completed(self, instance):
		parent = instance.ad_set
		if parent and parent.status == "COMPLETED":                
			return True
		return False
	
# ========================================================
	def get_ads_performance(self, instance):
		start_date = self.context['start_date']
		end_date = self.context['end_date']
		# platforms = instance.platforms.lower()
		platforms = ''
		# print("platforms: ", start_date)
		platformsArr = ""
		if len(platforms) > 0:
			platformsArr = platforms.split(",")
		# print("platformsArr: ", platformsArr)        
		if start_date != "null" and end_date != "null":
			query = Q(publisher_platform__in=platformsArr, ad_id=instance.id, date__gte=start_date, date__lte=end_date)
		else:
			query = Q(publisher_platform__in=platformsArr, ad_id=instance.id)            
		queryset = instance.ads_performance.values("publisher_platform", "ad_platform") \
						.annotate(id=Min('id'), impressions=Sum('impressions'), clicks=Sum('clicks'), actions=Sum('actions'),spend=Sum('spend'),earned=Sum('earned'),) \
						.filter(query)
		# querysetAll = list(chain(queryset, querysetPlatforms))  
		context = {"ad_id": instance.id}    
		return AdsPerformanceSerializer(queryset,
								  many=True, context=context).data

	def get_ads_platform(self, instance):
		start_date = self.context['start_date']
		end_date = self.context['end_date']
		query = Q(ad_id=instance.id)
		queryset = instance.ads_platform.filter(query)
		context = {"ad_id": instance.id, "start_date": start_date, "end_date": end_date}  
		# print("get_ads_platform: ", context)
		return AdsPlatformsSerializer(queryset,
								  many=True, context=context).data
	
	def get_ads_platform_strings(self, instance):
		query = Q(ad_id=instance.id)
		queryset = instance.ads_platform.filter(query).order_by('-publisher_platform')
		result = ''
		for item in queryset:
			publisher_platform = item.publisher_platform
			publisher_platform = publisher_platform.capitalize()
			result += publisher_platform + ','
		if len(result) > 0:
			result = result[:-1]
		return result
	
class PlatformsSerializer(serializers.Serializer):
	media_id = serializers.IntegerField(required=False)
	name = serializers.CharField(required=False)
	statuses = serializers.CharField(required=False)
	media_display_file_name = serializers.CharField(required=False)

def checkPlatform(publisherPlatform):
	if publisherPlatform == "Facebook" or publisherPlatform == "Instagram" or publisherPlatform == "Meta" or publisherPlatform == "Messenger":
		return "meta"
	if publisherPlatform == "Google" or publisherPlatform == "Youtube":
		return "google"
	if publisherPlatform == "LinkedIn":
		return "linkedin"
	if publisherPlatform == "Pinterest":
		return "pinterest"
	if publisherPlatform == "Snapchat":
		return "snapchat"
	if publisherPlatform == "Tiktok":
		return "tiktok"
	return "noname"

class AdsUpdateSerializer(serializers.ModelSerializer):
	id = serializers.IntegerField(required=False)
	user = UserSerializer(required=False)
	ad_set = AdSetsBasicSerializer(required=False)
	campaign = CampaignsBasicSerializer(required=False)
	status = serializers.CharField(required=False)
	ads_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
	destination_url = serializers.CharField(required=False)
	display_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	name = serializers.CharField(required=False)
	# 
	campaign_id = serializers.IntegerField(required=False)
	ad_set_id = serializers.IntegerField(required=False) 
	media_id = serializers.IntegerField(required=False)  
	# 
	
	facebook_page = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	facebook_page_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	headline = serializers.CharField(required=False, allow_blank=True)
	primary_text = serializers.CharField(required=False, allow_blank=True)
	description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	# 
	instagram_account = serializers.CharField(required=False, allow_null=True, allow_blank=True)    
	instagram_account_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)    
	# 
	call_to_action_linkedin = serializers.CharField(required=False, allow_null=True, allow_blank=True)    
	# 
	call_to_action_snapchat = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	brand_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	# 
	pinterest_board = serializers.CharField(required=False, allow_null=True, allow_blank=True) 
	pinterest_board_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)     
	# 
	call_to_action_tiktok = serializers.CharField(required=False, allow_null=True, allow_blank=True)
	# 
	platforms = PlatformsSerializer(required=False, many=True)  
	# 
	media_ids = serializers.CharField(required=False) 
	call_to_action_meta = serializers.CharField(required=False, allow_null=True, allow_blank=True)   
	# 
	ad_id = serializers.IntegerField(required=False)
	status_run_on  = serializers.BooleanField(required=False)
	publisher_platform = serializers.CharField(required=False)
	platform_not_run_on = serializers.CharField(required=False, allow_blank=True)
	
	class Meta:
		model = Ads
		fields = '__all__'

	def changeStatusRunPause(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			status = self.validated_data['status']        
			ads_ids = self.validated_data['ads_ids']
			disabled = self.validated_data['disabled']              
			ads = Ads.objects.filter(user_id=user_id, id__in=ads_ids)

			for a in ads:
				a.status = status
				a.disabled = disabled
				a.save()

				for ap in a.ads_platform.all():
					if disabled:
						ap.status = status
						ap.previously_disabled = ap.disabled
						ap.disabled = disabled
					else:
						if not ap.previously_disabled:
							ap.status = ap.ad.status
						ap.disabled = ap.previously_disabled

					ap.save()

			return AdsTempSerializer(ads, many=True).data
		except Exception as error:
			print("AdsUpdateSerializer_changeStatusRunPause_error: ", error)
			return False

	def delete(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			ads_ids = self.validated_data['ads_ids']
			Ads.objects.filter(user_id=user_id, id__in=ads_ids).update(is_deleted=True)
			return True
		except Exception as error:
			print("AdsUpdateSerializer_delete_error: ", error)
			return False

	def add_from_campaign_and_ad_set(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			campaign_id = self.validated_data['campaign_id'] 
			destination_url = self.validated_data['destination_url']
			display_url = self.validated_data['display_url']         
			ad_set_id = self.validated_data['ad_set_id'] 
			# 
			model = Ads.objects.create(user_id=user_id, campaign_id=campaign_id, ad_set_id=ad_set_id, destination_url=destination_url, display_url=display_url)
			model.save()
			return True
		except Exception as error:
			print("AdsUpdateSerializer_add_from_campaign_and_ad_set_error: ", error)
			return False

	def update(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			ad_id = self.validated_data['id'] 
			destination_url = self.validated_data['destination_url']
			display_url = self.validated_data['display_url']
			headline = self.validated_data['headline'] 
			primary_text = self.validated_data['primary_text']
			description = self.validated_data['description']            
			name = self.validated_data['name']

			ad = Ads.objects.get(user_id=user_id, id=ad_id)
			ad.destinnation_url = destination_url
			ad.display_url = display_url
			ad.headline = headline
			ad.primary_text = primary_text
			ad.description = description
			ad.name = name
			ad.save()

			try:
				linkedin_platform = ad.ads_platform.get(ad_platform='linkedin')

				if linkedin_platform.api_id:
					new_ad = {
						'name': name
					}

					access_token = Authorizations.objects.get(user_id=user_id, ad_platform='linkedin').access_token

					async_task(update_linkedin_ad, access_token, linkedin_platform.api_id, new_ad, hook=send_notif)
			except AdsPlatforms.DoesNotExist:
				pass

			return AdsTempSerializer(ad).data
		except Exception as error:
			print("AdsUpdateSerializer_update_error: ", error)
			return False

	def add_common(self, request):
		try:
			print("Ads add_common")
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			name = self.validated_data['name']
			campaign_id = self.validated_data['campaign_id'] 
			destination_url = self.validated_data['destination_url']
			display_url = self.validated_data['display_url']           
			ad_set_id = self.validated_data['ad_set_id'] 
			status = "ACTIVE"            
			platforms = self.validated_data['platforms'] 
			#
			description = self.validated_data['description'] 
			headline = self.validated_data['headline']
			primary_text = self.validated_data['primary_text'] 
			brand_name = self.validated_data['brand_name']           
			# 
			facebook_page = self.validated_data['facebook_page']
			facebook_page_id = self.validated_data['facebook_page_id']
			instagram_account = self.validated_data['instagram_account']
			instagram_account_id = self.validated_data['instagram_account_id']
			pinterest_board = self.validated_data['pinterest_board']
			pinterest_board_id = self.validated_data['pinterest_board_id']
			call_to_action_snapchat = self.validated_data['call_to_action_snapchat']
			call_to_action_tiktok = self.validated_data['call_to_action_tiktok']
			call_to_action_linkedin = self.validated_data['call_to_action_linkedin'] 
			call_to_action_meta = self.validated_data['call_to_action_meta']  
			#
			platform_not_run_on = self.validated_data['platform_not_run_on']    
			# 
			# countAdsExist = Ads.objects.filter(user_id=user_id,campaign_id=campaign_id, ad_set_id=ad_set_id,media_id=media_id).count()
			# if countAdsExist == 0:
			ads = []
			ads_platforms = []

			with transaction.atomic():
				for _platform in platforms:
					print('platform is ')
					print(_platform)
					# print("platforms: ", _platform)
					media_id = _platform['media_id']
					media = Media.objects.get(id=media_id)

					if media.thumb_video:
						image = Image.open(media.thumb_video)
						# Create a thumbnail
						thumbnail_size = (300, 300)
						thumbnail = image.copy()
						thumbnail.thumbnail(thumbnail_size)
					else:

						# Open the original image
						image = Image.open(media.file)
						
						# Create a thumbnail
						thumbnail_size = (300, 300)
						thumbnail = image.copy()
						thumbnail.thumbnail(thumbnail_size)
											

					file_type = image.format
					
					# Generate a UUID for the thumbnail file name
					thumbnail_uuid = str(uuid.uuid4())
					thumbnail_file_name = f'thumbs/{thumbnail_uuid}.{file_type}'

					# Save the image and thumbnail to S3
					with BytesIO() as output:
						thumbnail.save(output, format=file_type)
						output.seek(0)
						thumbnail_file = ContentFile(output.getvalue())
						actual_thumb_name = default_storage.save(thumbnail_file_name, thumbnail_file)
					
			
					name = headline + " " + _platform['media_display_file_name']
					adsModel = Ads.objects.create(user_id=user_id, name=name, campaign_id=campaign_id, ad_set_id=ad_set_id, destination_url=destination_url, display_url=display_url, media_id=_platform['media_id'], thumbnail=actual_thumb_name, status=status, disabled=False, 
					description=description, headline=headline, primary_text=primary_text, facebook_page=facebook_page, facebook_page_id=facebook_page_id,
					instagram_account=instagram_account, instagram_account_id=instagram_account_id, pinterest_board=pinterest_board,
					call_to_action_snapchat=call_to_action_snapchat, call_to_action_tiktok=call_to_action_tiktok, brand_name=brand_name, call_to_action_linkedin=call_to_action_linkedin, pinterest_board_id=pinterest_board_id, call_to_action_meta=call_to_action_meta)

					ads.append(adsModel)

					try:
						publisherPlatformsTempName = _platform['name']
						publisherPlatformsTempArr = publisherPlatformsTempName.split(",")
						statusesTempName = _platform['statuses']
						statusesTempArr = statusesTempName.split(":::")
						count = 0
						for _publisher_platform in publisherPlatformsTempArr:
							_publisher_platform_lower = _publisher_platform.lower()
							if _publisher_platform_lower == "meta":
								_publisher_platform_lower = "audience_network"
							_statuses = statusesTempArr[count]
							_disabled = False
							_status = "ACTIVE"
							if _statuses and (_statuses == "undefined" or _statuses == "null"):
								
								print(_publisher_platform)
								_disabled = True
								_status = "DRAFT"
								# print("_statuses+_publisher_platform_lower: ", _statuses)
							# countCampaign = CampaignsPlatforms.objects.filter(campaign_id=campaign_id, publisher_platform=_publisher_platform_lower).count()
							# if countCampaign == 0:
							#     _ad_platform = checkPlatform(_publisher_platform)
							#     if _publisher_platform_lower in platform_not_run_on:
							#         CampaignsPlatforms.objects.create(campaign_id=campaign_id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled, run_on=False)
							#     else:
							#         CampaignsPlatforms.objects.create(campaign_id=campaign_id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled)
							#     # 
							# countAdSet = AdSetsPlatforms.objects.filter(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower).count()
							# if countAdSet == 0:
							#     _ad_platform = checkPlatform(_publisher_platform)
							#     if _publisher_platform_lower in platform_not_run_on:
							#         AdSetsPlatforms.objects.create(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled, run_on=False)
							#     else:
							#         AdSetsPlatforms.objects.create(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled)
							countAds = AdsPlatforms.objects.filter(ad_id=adsModel.id, publisher_platform=_publisher_platform_lower).count()
							if countAds == 0:
								
								print(_publisher_platform)
								_ad_platform = checkPlatform(_publisher_platform)
								if _publisher_platform_lower in platform_not_run_on:
									
									adsPlatformsModel = AdsPlatforms.objects.create(ad_id=adsModel.id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled, run_on=False)

									countCampaign = CampaignsPlatforms.objects.filter(campaign_id=campaign_id, publisher_platform=_publisher_platform_lower).count()
									if countCampaign == 0:
										CampaignsPlatforms.objects.create(campaign_id=campaign_id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled)
									# else:
									#     CampaignsPlatforms.objects.filter(campaign_id=campaign_id, publisher_platform=_publisher_platform_lower, run_on=False).update(run_on=True)
									# 
									countAdSet = AdSetsPlatforms.objects.filter(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower).count()
									if countAdSet == 0:
										
										AdSetsPlatforms.objects.create(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled)
									# else:
									#     AdSetsPlatforms.objects.filter(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower, run_on=False).update(run_on=True)
								else: 
									
									adsPlatformsModel = AdsPlatforms.objects.create(ad_id=adsModel.id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled)

									countCampaign = CampaignsPlatforms.objects.filter(campaign_id=campaign_id, publisher_platform=_publisher_platform_lower).count()
									if countCampaign == 0:
										CampaignsPlatforms.objects.create(campaign_id=campaign_id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled)
									else:
										CampaignsPlatforms.objects.filter(campaign_id=campaign_id, publisher_platform=_publisher_platform_lower).update(disabled=False, status='ACTIVE')
									# 
									countAdSet = AdSetsPlatforms.objects.filter(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower).count()
									if countAdSet == 0:
										AdSetsPlatforms.objects.create(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled)
									else:
										AdSetsPlatforms.objects.filter(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower).update(disabled=False, status='ACTIVE')

								ads_platforms.append(adsPlatformsModel)
							# else:
							#     # cam1 : 9=>18 , adset 1: 6=>15
							#     countAds = AdsPlatforms.objects.filter(ad_id=adsModel.id, publisher_platform=_publisher_platform_lower).count()
							#     if countAds == 0:
							#         _ad_platform = checkPlatform(_publisher_platform)
							#         if _publisher_platform_lower in platform_not_run_on:
							#             AdsPlatforms.objects.create(ad_id=adsModel.id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled, run_on=False)
							#         else: 
							#             AdsPlatforms.objects.create(ad_id=adsModel.id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled)
							#     countAdSet = AdSetsPlatforms.objects.filter(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower).count()
							#     if countAdSet == 0:
							#         _ad_platform = checkPlatform(_publisher_platform)
							#         if _publisher_platform_lower in platform_not_run_on:
							#             AdSetsPlatforms.objects.create(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled, run_on=False)
							#         else:
							#             AdSetsPlatforms.objects.create(ad_set_id=ad_set_id, publisher_platform=_publisher_platform_lower, ad_platform=_ad_platform, status=_status, disabled=_disabled)
							#     else:
							#         try:
							#             lau = 0
							#         except Exception as err:
							#             print("AdsUpdateSerializer_add_common_campaign_for_platforms_error_e
							count += 1
					except Exception as error:
						print("AdsUpdateSerializer_add_common_campaign_for_platforms_error: ", error)

					print(" .....")		
			# 
			platforms_ad_set = ""
			platforms_ad_set_list = AdSetsPlatforms.objects.filter(ad_set_id=ad_set_id)
			for item in platforms_ad_set_list:
				platforms_ad_set += item.publisher_platform + ","
			if len(platforms_ad_set) > 0:
				platforms_ad_set = platforms_ad_set[:-1]
			AdSets.objects.filter(user_id=user_id, id=ad_set_id).update(disabled=False, status=status)
			# 
			platforms_campaign = ""
			platforms_campaign_list = CampaignsPlatforms.objects.filter(campaign_id=campaign_id)
			for item in platforms_campaign_list:
				platforms_campaign += item.publisher_platform + ","
			if len(platforms_campaign) > 0:
				platforms_campaign = platforms_campaign[:-1]            
			# 
			try:
				model_campaign = Campaigns.objects.get(id=campaign_id)
				if model_campaign.status == "DRAFT":
					status = "ACTIVE"
					Campaigns.objects.filter(user_id=user_id, id=campaign_id).update(disabled=False, status=status) 
				elif model_campaign.status != "ACTIVE":
					Campaigns.objects.filter(user_id=user_id, id=campaign_id).update(disabled=False)
				else:
					Campaigns.objects.filter(user_id=user_id, id=campaign_id).update(disabled=False, status=status)                    
			except Exception as err:
				pass

			return {
				'ads': AdsTempSerializer(ads, many=True).data,
				'ads_platforms': AdsPlatformsTempSerializer(ads_platforms, many=True).data,
				'campaigns_platforms': CampaignsPlatformsTempSerializer(CampaignsPlatforms.objects.filter(campaign_id=campaign_id), many=True).data,
				'ad_sets_platforms': AdsetsPlatformsTempSerializer(AdSetsPlatforms.objects.filter(ad_set_id=ad_set_id), many=True).data,
				'campaign': CampaignsBasicUnGroupSerializer(Campaigns.objects.get(id=campaign_id)).data,
				'ad_set': AdSetsTempSerializer(AdSets.objects.get(id=ad_set_id)).data,
			}
		except Exception as e:
			print("Error", e)
			print("AdsUpdateSerializer_add_common_error: ", e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
		
	# ==============

	# Video  Facebook,Instagram,Pinterest
	def update_min1080x1080_video(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			name = self.validated_data['name']
			destination_url = self.validated_data['destination_url']
			display_url = self.validated_data['display_url']        
			ads_id = self.validated_data['id'] 
			headline = self.validated_data['headline'] 
			primary_text = self.validated_data['primary_text'] 
			description = self.validated_data['description'] 
			# 
			 
			facebook_page = self.validated_data['facebook_page'] 
			facebook_page_id = self.validated_data['facebook_page_id']
			instagram_account = self.validated_data['instagram_account'] 
			instagram_account_id = self.validated_data['instagram_account_id'] 
			pinterest_board = self.validated_data['pinterest_board']
			pinterest_board_id = self.validated_data['pinterest_board_id'] 
			# 
			call_to_action_meta = self.validated_data['call_to_action_meta'] 
			#  
			model = Ads.objects.get(user_id=user_id, id=ads_id)
			model.name = name
			model.destination_url = destination_url
			model.display_url = display_url
			model.headline = headline
			model.primary_text = primary_text
			model.description = description
			
			model.facebook_page = facebook_page
			model.facebook_page_id = facebook_page_id
			model.instagram_account = instagram_account
			model.instagram_account_id = instagram_account_id
			model.pinterest_board = pinterest_board
			model.pinterest_board_id = pinterest_board_id
			# 
			model.call_to_action_meta = call_to_action_meta
			model.save()
			try:
				AdsPlatforms.objects.filter(ad_id=ads_id, status="DRAFT", disabled=1, publisher_platform="facebook").update(status="PAUSED")
				AdsPlatforms.objects.filter(ad_id=ads_id, status="DRAFT", disabled=1, publisher_platform="instagram").update(status="PAUSED")
				AdsPlatforms.objects.filter(ad_id=ads_id, status="DRAFT", disabled=1, publisher_platform="pinterest").update(status="PAUSED")
			except Exception as err:    
				pass
			return True
		except Exception as error:
			print("AdsUpdateSerializer_update_min1080x1080_video_error: ", error)
			return False

	def update_1080x1920_video(self, request):
		try:
			user_id = _get_user_id_from_token(request) 
			# user_id = 2 
			name = self.validated_data['name']
			destination_url = self.validated_data['destination_url'] 
			display_url = self.validated_data['display_url']          
			ads_id = self.validated_data['id'] 
			headline = self.validated_data['headline'] 
			primary_text = self.validated_data['primary_text'] 
			description = self.validated_data['description'] 
			# 
			 
			facebook_page = self.validated_data['facebook_page'] 
			facebook_page_id = self.validated_data['facebook_page_id']            
			instagram_account = self.validated_data['instagram_account'] 
			instagram_account_id = self.validated_data['instagram_account_id'] 
			pinterest_board = self.validated_data['pinterest_board']
			pinterest_board_id = self.validated_data['pinterest_board_id'] 
			call_to_action_snapchat = self.validated_data['call_to_action_snapchat'] 
			brand_name = self.validated_data['brand_name']
			call_to_action_tiktok = self.validated_data['call_to_action_tiktok']
			# 
			call_to_action_meta = self.validated_data['call_to_action_meta'] 
			#  
			model = Ads.objects.get(user_id=user_id, id=ads_id)
			model.name = name
			model.destination_url = destination_url
			model.display_url = display_url
			model.headline = headline
			model.primary_text = primary_text
			model.description = description
			
			model.facebook_page = facebook_page
			model.facebook_page_id = facebook_page_id
			model.call_to_action_tiktok = call_to_action_tiktok
			model.instagram_account = instagram_account
			model.instagram_account_id = instagram_account_id
			model.pinterest_board = pinterest_board
			model.pinterest_board_id = pinterest_board_id
			model.call_to_action_snapchat = call_to_action_snapchat
			model.brand_name = brand_name
			# 
			model.call_to_action_meta = call_to_action_meta
			model.save()
			try:
				AdsPlatforms.objects.filter(ad_id=ads_id, status="DRAFT", disabled=1, publisher_platform="facebook").update(status="PAUSED")
				AdsPlatforms.objects.filter(ad_id=ads_id, status="DRAFT", disabled=1, publisher_platform="instagram").update(status="PAUSED")
				AdsPlatforms.objects.filter(ad_id=ads_id, status="DRAFT", disabled=1, publisher_platform="pinterest").update(status="PAUSED")
				AdsPlatforms.objects.filter(ad_id=ads_id, status="DRAFT", disabled=1, publisher_platform="snapchat").update(status="PAUSED")
			except Exception as err:    
				pass
			return True
		except Exception as error:
			print("AdsUpdateSerializer_update_1080x1920_video_error: ", error)
			return False

	def update_status_run_on(self, request):
		try:
			ad_id = self.validated_data['ad_id']
			publisher_platform = self.validated_data['publisher_platform']           
			status_run_on = self.validated_data['status_run_on'] 
			model = AdsPlatforms.objects.get(ad_id=ad_id, publisher_platform=publisher_platform)
			model.run_on = status_run_on
			model.save()
			try:
				ads_model = Ads.objects.get(id=ad_id)
				ad_set_id = ads_model.ad_set_id                
				model_ad_set = AdSetsPlatforms.objects.get(ad_set_id=ad_set_id, publisher_platform=publisher_platform)
				#model_ad_set.run_on = status_run_on
				model_ad_set.save()
				try:
					campaign_id = ads_model.campaign_id
					model_campaign = CampaignsPlatforms.objects.get(campaign_id=campaign_id, publisher_platform=publisher_platform)
					#model_campaign.run_on = status_run_on
					model_campaign.save()
				except Exception as err:
					print("AdsUpdateSerializer_update_status_run_on_error_cam: ", err)
			except Exception as err:
				print("AdsUpdateSerializer_update_status_run_on_error_ad_set: ", err)
			return True
		except Exception as error:
			print("AdsUpdateSerializer_update_status_run_on_error: ", error)
			return False

class AdsPlatformsSerializer(serializers.ModelSerializer):
	ad = AdsBasicSerializer(required=False, many=False)
	ads_performance = serializers.SerializerMethodField(method_name="get_ads_performance")

	class Meta:
		model = AdsPlatforms
		fields = '__all__'

	def get_ads_performance(self, instance):
		# print("get_ads_performance: ", instance.publisher_platform)
		publisher_platform = instance.publisher_platform
		ad_platform = instance.ad_platform
		# ad_id = instance.campaign.id
		if self.context:
			start_date = self.context['start_date']
			end_date = self.context['end_date']        
			ad_id = self.context['ad_id']
			# print("ad_id: ", ad_id)
			if start_date != "null" and end_date != "null":
				query = Q(ad_id=ad_id, publisher_platform=publisher_platform, ad_platform=ad_platform, date__gte=start_date, date__lte=end_date)
			else:
				query = Q(ad_id=ad_id, publisher_platform=publisher_platform, ad_platform=ad_platform)
			queryset = AdsPerformance.objects.values("publisher_platform", "ad_platform") \
							.annotate(id=Min('id'), impressions=Sum('impressions'), clicks=Sum('clicks'), actions=Sum('actions'),spend=Sum('spend'),earned=Sum('earned'),) \
							.filter(query)
			# print("queryset: ", queryset)
			return AdsPerformanceSerializer(queryset,
									  many=True).data
		
class AdsPerformanceSerializer(serializers.ModelSerializer):
	ad = AdsBasicSerializer(required=False, many=False)
	# ads_platform = serializers.SerializerMethodField(method_name="get_ads_platform")
	
	class Meta:
		model = AdsPerformance
		fields = '__all__'

	def get_ads_platform(self, instance):
		ad_id = self.context['ad_id']
		# print("get_ads_platform: ", instance["ad_platform"])        
		queryset = AdsPlatforms.objects.filter(ad_id=ad_id, ad_platform=instance["ad_platform"], publisher_platform=instance["publisher_platform"])
		return AdsPlatformsSerializer(queryset,
								  many=True).data


class AdsPerformanceUpdateSerializer(serializers.ModelSerializer):
	id = serializers.IntegerField(required=False)
	user = UserSerializer(required=False)
	ad = AdsBasicSerializer(required=False)
	count_authenticated_social = serializers.IntegerField(required=False)
	ads_id = serializers.IntegerField(required=False)
	
	class Meta:
		model = AdsPerformance
		fields = '__all__'

	def changeStatusRunPause(self, request):
		try:
			status = self.validated_data['status']        
			id = self.validated_data['id']
			disabled = self.validated_data['disabled']             

			AdsPlatforms.objects.filter(id=id).update(status=status, disabled=disabled)

			count_authenticated_social = self.validated_data['count_authenticated_social']
			ads_id = self.validated_data['ads_id']

			# query = Q(ad_id=ads_id, status="PAUSED", disabled=1)
			# count_ad_platform_paused = AdsPlatforms.objects.filter(query).count()

			# if count_ad_platform_paused >= count_authenticated_social and count_ad_platform_paused > 0 and disabled == 1:
			# 	print("OK...:", disabled)  
			# 	Ads.objects.filter(id=ads_id).update(status="ALL PAUSED", disabled=1)
			# else:
			# 	print("ACTIVE...:")
			# 	Ads.objects.filter(id=ads_id).update(status="ACTIVE", disabled=0)

			ad = Ads.objects.get(id=ads_id)

			if status == 'PAUSED':
				active_platforms = AdsPlatforms.objects.filter(ad_id=ad.id, run_on=True, publisher_platform__in=[a.publisher_platform for a in ad.ads_platform.exclude(status='PAUSED')]).exists()

				if not active_platforms:
					ad.status = 'PAUSED'
			else:
				ad.status = status

			ad.disabled = False
			ad.save()

			return AdsTempSerializer(ad).data
		except Exception as error:
			print("AdsPerformanceUpdateSerializer_changeStatusRunPause_error: ", error)
			return False

class AdsPlatformsUpdateSerializer(serializers.ModelSerializer):
	ad = AdsBasicSerializer(required=False)
	ad_platform_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
	
	class Meta:
		model = AdsPlatforms
		fields = '__all__'

	def changeStatusRunPause(self, request):
		try:
			status = self.validated_data['status']        
			ad_platform_ids = self.validated_data['ad_platform_ids']
			disabled = self.validated_data['disabled']             

			ads_platforms = AdsPlatforms.objects.filter(id__in=ad_platform_ids)

			for ap in ads_platforms:
				ap.status = status
				ap.disabled = disabled
				ap.save()

				Ads.objects.filter(id=ap.ad.id).update(disabled=False)

			return True
		except Exception as error:
			print("AdsPlatformsUpdateSerializer_changeStatusRunPause_error: ", error)
			return False

class AdsBasicUnGroupSerializer(serializers.ModelSerializer):
	user = UserSerializer(required=False)
	media = MediaSerializer(required=False, many=False)
	ads_platform_strings = serializers.SerializerMethodField(method_name="get_ads_platform_strings")
	ads_platform = serializers.SerializerMethodField(method_name="get_ads_platform")
	
	class Meta:
		model = Ads
		fields = '__all__'

	def get_ads_platform_strings(self, instance):
		query = Q(ad_id=instance.id)
		queryset = instance.ads_platform.filter(query).order_by('-publisher_platform')
		result = ''
		for item in queryset:
			publisher_platform = item.publisher_platform
			publisher_platform = publisher_platform.capitalize()
			result += publisher_platform + ','
		if len(result) > 0:
			result = result[:-1]
		return result
	
	def get_ads_platform(self, instance):
		# start_date = self.context['start_date']
		# end_date = self.context['end_date']
		query = Q(ad_id=instance.id)
		queryset = instance.ads_platform.filter(query)
		# context = {"ad_id": instance.id, "start_date": start_date, "end_date": end_date}  
		# print("get_ads_platform: ", context)
		return AdsPlatformsSerializer(queryset,
								  many=True).data

class AdsPerformanceUnGroupSerializer(serializers.ModelSerializer):
	ad = AdsBasicSerializer(required=False, many=False)
	ad_current = serializers.SerializerMethodField(method_name="get_ad_current")
	ad_platforms = serializers.SerializerMethodField(method_name="get_ad_platforms")
	ad_name = serializers.CharField(required=False)

	class Meta:
		model = AdsPerformance
		fields = '__all__'
		extra_fields =  [
			'ad_name'
		]

	def get_ad_platforms(self, instance):
		# print("get_ad_platform: ", instance['ad_id'])
		# print("get_ad_platform0: ", instance['ad_name'])
		ad_id = instance['ad_id']
		ad_platform = instance['ad_platform']
		publisher_platform = instance['publisher_platform']
		# print("get_ad_platform1: ", instance["ad_platform"])        
		queryset = AdsPlatforms.objects.filter(ad_id=ad_id, ad_platform=ad_platform, publisher_platform=publisher_platform)
		# print("get_ad_platform2: ", queryset)      
		return AdsPlatformsSerializer(queryset,
								  many=True).data
	

	def get_ad_current(self, instance):
		# print("get_ad_platform: ", instance['ad_name'])
		ad_id = instance['ad_id']
		queryset = Ads.objects.filter(id=ad_id)
		return AdsBasicUnGroupSerializer(queryset,
								  many=True).data

class AdsPlatformsUnGroupSerializer(serializers.ModelSerializer):
	ads_performance = serializers.SerializerMethodField(method_name="get_ads_performance")
	ad_current = serializers.SerializerMethodField(method_name="get_ad_current")
	
	class Meta:
		model = AdsPlatforms
		fields = '__all__'

	def get_ads_performance(self, instance):
		# print("get_ads_performance: ", instance.publisher_platform)
		publisher_platform = instance.publisher_platform
		ad_platform = instance.ad_platform
		ad_id = instance.ad_id
		if self.context:
			start_date = self.context['start_date']
			end_date = self.context['end_date']
			# print("ad_id: ", ad_id)
			if start_date != "null" and end_date != "null":
				query = Q(ad_id=ad_id, publisher_platform=publisher_platform, ad_platform=ad_platform, date__gte=start_date, date__lte=end_date)
			else:
				query = Q(ad_id=ad_id, publisher_platform=publisher_platform, ad_platform=ad_platform)
			queryset = AdsPerformance.objects.values("publisher_platform", "ad_platform") \
							.annotate(id=Min('id'), impressions=Sum('impressions'), clicks=Sum('clicks'), actions=Sum('actions'),spend=Sum('spend'),earned=Sum('earned'),) \
							.filter(query)
			# print("queryset: ", queryset)
			return AdsPerformanceSerializer(queryset,  many=True).data
	   
	def get_ad_current(self, instance):
		ad_id = instance.ad_id
		queryset = Ads.objects.filter(id=ad_id)
		return AdsBasicUnGroupSerializer(queryset,
								  many=True).data
	
# class AdsMediaSerializer(serializers.ModelSerializer):
	
#     class Meta:
#         model = AdsMedia
#         fields = '__all__'

# Ads End =========================================
class AdsetsPlatformsTempSerializer(serializers.ModelSerializer):
	class Meta:
		model = AdSetsPlatforms
		fields = '__all__'


class AdSetsTempSerializer(serializers.ModelSerializer):
	user = UserSerializer(required=False)
	languages_w_ad_set = serializers.SerializerMethodField(method_name="get_languages_w_ad_set")
	locations_w_ad_set = serializers.SerializerMethodField(method_name="get_locations_w_ad_set")
	keywords_w_ad_set = serializers.SerializerMethodField(method_name="get_keywords_w_ad_set")
	ad_sets_platforms = AdsetsPlatformsTempSerializer(many=True, source='ad_sets_platform')

	class Meta:
		model = AdSets
		fields = '__all__'

	def get_languages_w_ad_set(self, instance):
		queryset = instance.languages_w_ad_set.filter()
		return AdSetsLanguagesSerializer(queryset,
								  many=True).data
	def get_locations_w_ad_set(self, instance):
		queryset = instance.locations_w_ad_set.filter()
		return AdSetsLocationsSerializer(queryset,
								  many=True).data
	def get_keywords_w_ad_set(self, instance):
		queryset = instance.keywords_w_ad_set.filter()
		return AdSetsKeywordsSerializer(queryset,
								  many=True).data



class AdsPlatformsTempSerializer(serializers.ModelSerializer):
	campaign_id = serializers.IntegerField(source='ad.campaign_id')
	ad_set_id = serializers.IntegerField(source='ad.ad_set_id')
	ad_id = serializers.IntegerField()

	class Meta:
		model = AdsPlatforms
		fields = '__all__'

class AdsTempSerializer(serializers.ModelSerializer):
	user = UserSerializer(required=False)
	media = MediaSerializer(required=False, many=False)
	ads_platforms = AdsPlatformsTempSerializer(many=True, source='ads_platform') 

	class Meta:
		model = Ads
		fields = '__all__'

class AdsPerformanceTempSerializer(serializers.ModelSerializer):
	ad = AdsBasicSerializer(required=False, many=False)
	campaign_id = serializers.SerializerMethodField()
	ad_set_id = serializers.SerializerMethodField()
	ad_id = serializers.IntegerField() 
	
	class Meta:
		model = AdsPerformance
		fields = '__all__'
	
	def ad_queryset(self, instance):
		return Ads.objects.get(id=instance.get('ad_id'))

	def get_campaign_id(self, instance):
		return self.ad_queryset(instance).campaign_id

	def get_ad_set_id(self, instance):
		return self.ad_queryset(instance).ad_set_id