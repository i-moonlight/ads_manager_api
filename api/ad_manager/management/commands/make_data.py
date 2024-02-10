# -*- coding: utf-8 -*-
#!/usr/bin/env python

from django.core.management.base import BaseCommand
from django.conf import settings
import sqlite3
from datetime import datetime, timedelta
import os
import sys
from io import BytesIO

import traceback

from django.core.files.uploadedfile import SimpleUploadedFile


import boto3
import cv2
from PIL import Image

from api.ad_manager.models import Campaigns, CampaignsPlatforms, AdSets, AdSetsPlatforms, Ads, AdsPlatforms, AdsPerformance
from api.media_library.models import Media

import random

# Connect to the SQLite file
conn = sqlite3.connect('../../db.sqlite3')

end_date = datetime.today().date()
start_date = (datetime.now() - timedelta(days=20)).date()

class Command(BaseCommand):
	help = 'This command generates mock data for the Ads Manager API'

	def handle(self, *args, **options):
		
		confirmation = input("\033[91mType 'I CONFIRM' to proceed. ALL CAMPAIGN, AD SET, and AD DATA WILL BE OVERWRITTEN\033[0m")
		if confirmation.strip().lower() != 'i confirm':
			print('Command aborted.')
			return
		
		#print('start command!')
		generate_ads()
		generate_ads_data()
		print('Ads Data Generated')

		conn.close()

def date_range(start_date, end_date):
	for n in range(int((end_date - start_date).days) + 1):
		yield start_date + timedelta(n)

def generate_ads():
	try:
		print('start generate_ads')
		Campaigns.objects.all().delete()
		CampaignsPlatforms.objects.all().delete()
		AdSets.objects.all().delete()
		AdSetsPlatforms.objects.all().delete()
		Ads.objects.all().delete()
		AdsPlatforms.objects.all().delete()
		AdsPerformance.objects.all().delete()

		platforms = [{'ad_platform': 'meta_ads', 'publisher_platform': 'facebook'}, {'ad_platform': 'meta_ads', 'publisher_platform': 'instagram'}, {'ad_platform': 'meta_ads', 'publisher_platform': 'messenger'}, {'ad_platform': 'meta_ads', 'publisher_platform': 'audience_network'}, {'ad_platform': 'linkedin', 'publisher_platform': 'linkedin'}, {'ad_platform': 'google', 'publisher_platform': 'google'}, {'ad_platform': 'google', 'publisher_platform': 'youtube'}, {'ad_platform': 'pinterest', 'publisher_platform': 'pinterest'}]

		folder_path = "api/ad_manager/management/commands/test_media"

		if not os.path.exists(folder_path):
			print(f"Folder '{folder_path}' does not exist.")
			return

		files = os.listdir(folder_path)
		file_count = 0
		# Get positive integer inputs between 1 and 100 for campaign_count, ad_set_count, and ad_count
		campaign_count = get_integer_input_within_range('Enter number of campaigns to generate (1-25): ', 1, 25)
		ad_set_count = get_integer_input_within_range('Enter number of ad sets to generate for each campaign (1-25): ', 1, 25)
		ad_count = get_integer_input_within_range('Enter number of ads to generate for each ad set (1-25): ', 1, 25)



		creative_ids = []
		for file_name in files:
			file_count += 1
			print('file number: ', file_count)
			print('file_name: ', file_name)
			file_path = folder_path + '/' + file_name
			file = open(file_path, 'rb')
			file = SimpleUploadedFile(name=file_name, content=file.read())
			display_file_name = file_name
			file_type = file_name.split('.')[1]
			file_name = file_name.split('.')[0]
			file_size = os.path.getsize(file_path)
			height = None
			width = None
			is_video = False
			thumb_video = None
			if file_type == 'png':
				file_type = 'image/png'
				with Image.open(file_path) as img:
					width, height = img.size
			elif file_type == 'mp4':
				file_type = 'video/mp4'
				is_video = True
				vidcap = cv2.VideoCapture(file_path)
				width = vidcap.get(cv2.CAP_PROP_FRAME_WIDTH)
				height = vidcap.get(cv2.CAP_PROP_FRAME_HEIGHT)
				
				# Extract the first frame of the video as a thumbnail
				success,frame = vidcap.read()
				thumbnail = Image.fromarray(frame)
				# Resize the thumbnail image to the desired size
				thumbnail_size = (300, 300)  # replace with your desired size
				thumbnail.thumbnail(thumbnail_size, Image.ANTIALIAS)
				# Convert the thumbnail image to bytes and upload it to S3
				thumbnail_bytes = BytesIO()
				thumbnail.save(thumbnail_bytes, format='png')
				thumbnail_bytes.seek(0)
				s3 = boto3.client('s3')
				s3.upload_fileobj(thumbnail_bytes, settings.AWS_STORAGE_BUCKET_NAME, 'media_files/' + file_name + '.png')
				s3.put_object_acl(ACL='public-read', Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key= 'media_files/' + file_name + '.png')
				# Release the OpenCV resources
				vidcap.release()
				cv2.destroyAllWindows()

				thumb_video = 'media_files/' + file_name + '.png'

			mediaModal = Media.objects.create(user_id=1, file=file, display_file_name=display_file_name, file_type=file_type, size=file_size, width=width, height=height, is_video=is_video, thumb_video=thumb_video) 

			creative_id = mediaModal.id
			creative_ids.append(creative_id)


		# Create fake campaigns
		for i in range(int(campaign_count)):
			campaign_name = 'Campaign ' + str(i+1)
			campaignModal = Campaigns.objects.create(user_id=1, name=campaign_name, status='ACTIVE', disabled=0)

			for platform in platforms:
				CampaignsPlatforms.objects.create(campaign_id=campaignModal.id, ad_platform=platform['ad_platform'], publisher_platform=platform['publisher_platform'], status='ACTIVE', disabled=0, previously_disabled=0)

			# Create fake ad sets
			for j in range(int(ad_set_count)):
				ad_set_name = 'Ad Set ' + str(i+1) + ' - ' + str(j+1)
				ad_setModal = AdSets.objects.create(user_id=1, name=ad_set_name, campaign_id=campaignModal.id, status='ACTIVE', disabled=0)

				for platform in platforms:
					AdSetsPlatforms.objects.create(ad_set_id=ad_setModal.id, ad_platform=platform['ad_platform'], publisher_platform=platform['publisher_platform'], status='ACTIVE', disabled=0, previously_disabled=0)

				# Create fake ads
				for k in range(int(ad_count)):
					print('campaign: ', i+1, 'ad set: ', j+1, 'ad: ', k+1)
					ad_name = 'Ad ' + str(i+1) + ' - ' + str(j+1) + ' - ' + str(k+1)
					adModal = Ads.objects.create(user_id=1, name=ad_name, campaign_id=campaignModal.id, ad_set_id=ad_setModal.id, status='ACTIVE', media_id=creative_ids[random.randint(0, len(creative_ids)-1)],disabled=0)

					# Create fake ads platforms
					for platform in platforms:
						AdsPlatforms.objects.create(ad_id=adModal.id, ad_platform=platform['ad_platform'], publisher_platform=platform['publisher_platform'], status='ACTIVE', disabled=0, previously_disabled=0)

	
	except Exception as e:
		print("this is error", e)
		traceback.print_exc()  # Print the traceback information
		sys.exit()


def get_integer_input_within_range(prompt, min_value, max_value):
	while True:
		try:
			value = int(input(prompt))
			if min_value <= value <= max_value:
				return value
			else:
				print(f"Please enter an integer between {min_value} and {max_value}.")
		except ValueError:
			print("Invalid input. Please enter an integer.")

	

def generate_ads_data():
	try:

		AdsPerformance.objects.all().delete()

		# Get all AdsPlatforms
		ad_platforms = AdsPlatforms.objects.all()
	
		# Iterate over each AdsPlatforms
		for ad_platform in ad_platforms:
			ad_id = ad_platform.ad_id
			publisher_platform = ad_platform.publisher_platform
			run_on = ad_platform.run_on
			ad_platform = ad_platform.ad_platform
			# ad_platform changed here. 

			if run_on:	
				for single_date in date_range(start_date, end_date):
					print('Creating fake data for ad', ad_id, 'on', publisher_platform, 'for', single_date.strftime("%Y-%m-%d"))

					impressions = random.randrange(1000, 1000000)
					clicks = random.randrange(500, impressions)
					actions = random.randrange(50, clicks)
					spend = random.randrange(1000, 10000)
					earned = random.randrange(2000, 10000)

					ads_performance = AdsPerformance(
						ad_id=ad_id,
						date=single_date.strftime("%Y-%m-%d"),
						ad_platform=ad_platform,
						publisher_platform=publisher_platform,
						impressions=impressions,
						clicks=clicks,
						actions=actions,
						spend=spend,
						earned=earned
					)
					ads_performance.save()

	except Exception as e:
		print("this is error", e)
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
		print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
		sys.exit()



