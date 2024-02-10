# -*- coding: utf-8 -*-
#!/usr/bin/env python

from urllib.parse import urlparse
import sqlite3


from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from django.contrib.auth.models import User

from api.meta.models import *


from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative

from core.utils.slack import slack_alert_api_issue

# Connect to the SQLite file
conn = sqlite3.connect('../ads_manager_api/db.sqlite3')

META_SYSTEM_USER_ACCESS_TOKEN = getattr(settings, 'META_SYSTEM_USER_ACCESS_TOKEN')
META_APP_ID = getattr(settings, 'META_APP_ID')
META_APP_SECRET = getattr(settings, 'META_APP_SECRET')
META_API_VERSION = getattr(settings, 'META_API_VERSION')

no_insights = False
ads_only = False
get_languages = False
account_id = None
access_token = None

class Command(BaseCommand):
	help = 'This command does some thing'

	def handle(self, *args, **options):
		start_app()

def start_app():

	print('get_languages: ' + str(get_languages))
	get_facebook_language_data()
	return True
	

def get_facebook_language_data():
	base_url = f"https://graph.facebook.com/{META_API_VERSION}/search"
	#language_data = []

	language_data = [
		{
		"name": "English (US)",
		"key": 6
		},
		{
		"name": "Catalan",
		"key": 1
		},
		{
		"name": "Czech",
		"key": 2
		},
		{
		"name": "Cebuano",
		"key": 56
		},
		{
		"name": "Welsh",
		"key": 3
		},
		{
		"name": "Danish",
		"key": 4
		},
		{
		"name": "German",
		"key": 5
		},
		{
		"name": "Basque",
		"key": 59
		},
		{
		"name": "Spanish",
		"key": 23
		},
		{
		"name": "Spanish (Spain)",
		"key": 7
		},
		{
		"name": "Guarani",
		"key": 66
		},
		{
		"name": "Finnish",
		"key": 8
		},
		{
		"name": "French (France)",
		"key": 9
		},
		{
		"name": "Galician",
		"key": 65
		},
		{
		"name": "Hungarian",
		"key": 30
		},
		{
		"name": "Italian",
		"key": 10
		},
		{
		"name": "Japanese",
		"key": 11
		},
		{
		"name": "Korean",
		"key": 12
		},
		{
		"name": "Norwegian (bokmal)",
		"key": 13
		},
		{
		"name": "Norwegian (nynorsk)",
		"key": 84
		},
		{
		"name": "Dutch",
		"key": 14
		},
		{
		"name": "Frisian",
		"key": 63
		},
		{
		"name": "Polish",
		"key": 15
		},
		{
		"name": "Portuguese (Brazil)",
		"key": 16
		},
		{
		"name": "Portuguese (Portugal)",
		"key": 31
		},
		{
		"name": "Romanian",
		"key": 32
		},
		{
		"name": "Russian",
		"key": 17
		},
		{
		"name": "Slovak",
		"key": 33
		},
		{
		"name": "Slovenian",
		"key": 34
		},
		{
		"name": "Swedish",
		"key": 18
		},
		{
		"name": "Thai",
		"key": 35
		},
		{
		"name": "Turkish",
		"key": 19
		},
		{
		"name": "Northern Kurdish (Kurmanji)",
		"key": 76
		},
		{
		"name": "Simplified Chinese (China)",
		"key": 20
		},
		{
		"name": "Traditional Chinese (Hong Kong)",
		"key": 21
		},
		{
		"name": "Traditional Chinese (Taiwan)",
		"key": 22
		},
		{
		"name": "Afrikaans",
		"key": 36
		},
		{
		"name": "Albanian",
		"key": 87
		},
		{
		"name": "Armenian",
		"key": 68
		},
		{
		"name": "Azerbaijani",
		"key": 53
		},
		{
		"name": "Belarusian",
		"key": 54
		},
		{
		"name": "Bengali",
		"key": 45
		},
		{
		"name": "Bosnian",
		"key": 55
		},
		{
		"name": "Bulgarian",
		"key": 37
		},
		{
		"name": "Croatian",
		"key": 38
		},
		{
		"name": "Flemish",
		"key": 83
		},
		{
		"name": "English (UK)",
		"key": 24
		},
		{
		"name": "Esperanto",
		"key": 57
		},
		{
		"name": "Estonian",
		"key": 58
		},
		{
		"name": "Faroese",
		"key": 62
		},
		{
		"name": "French (Canada)",
		"key": 44
		},
		{
		"name": "Georgian",
		"key": 72
		},
		{
		"name": "Greek",
		"key": 39
		},
		{
		"name": "Gujarati",
		"key": 67
		},
		{
		"name": "Hindi",
		"key": 46
		},
		{
		"name": "Icelandic",
		"key": 69
		},
		{
		"name": "Indonesian",
		"key": 25
		},
		{
		"name": "Irish",
		"key": 64
		},
		{
		"name": "Javanese",
		"key": 71
		},
		{
		"name": "Kannada",
		"key": 75
		},
		{
		"name": "Kazakh",
		"key": 73
		},
		{
		"name": "Latvian",
		"key": 78
		},
		{
		"name": "Lithuanian",
		"key": 40
		},
		{
		"name": "Macedonian",
		"key": 79
		},
		{
		"name": "Malay",
		"key": 41
		},
		{
		"name": "Marathi",
		"key": 81
		},
		{
		"name": "Mongolian",
		"key": 80
		},
		{
		"name": "Nepali",
		"key": 82
		},
		{
		"name": "Punjabi",
		"key": 47
		},
		{
		"name": "Serbian",
		"key": 42
		},
		{
		"name": "Swahili",
		"key": 88
		},
		{
		"name": "Filipino",
		"key": 26
		},
		{
		"name": "Tamil",
		"key": 48
		},
		{
		"name": "Telugu",
		"key": 49
		},
		{
		"name": "Malayalam",
		"key": 50
		},
		{
		"name": "Ukrainian",
		"key": 52
		},
		{
		"name": "Uzbek",
		"key": 91
		},
		{
		"name": "Vietnamese",
		"key": 27
		},
		{
		"name": "Khmer",
		"key": 74
		},
		{
		"name": "Tajik",
		"key": 89
		},
		{
		"name": "Arabic",
		"key": 28
		},
		{
		"name": "Hebrew",
		"key": 29
		},
		{
		"name": "Urdu",
		"key": 90
		},
		{
		"name": "Persian",
		"key": 60
		},
		{
		"name": "Pashto",
		"key": 85
		},
		{
		"name": "Sinhala",
		"key": 86
		},
		{
		"name": "Japanese (Kansai)",
		"key": 70
		},
		{
		"name": "English (All)",
		"key": 1001
		},
		{
		"name": "Spanish (All)",
		"key": 1002
		},
		{
		"name": "French (All)",
		"key": 1003
		},
		{
		"name": "Chinese (All)",
		"key": 1004
		},
		{
		"name": "Portuguese (All)",
		"key": 1005
		}
	]
	
	'''
	# upgrade this to use pagination
	for letter in range(ord('a'), ord('z') + 1):
		query = chr(letter)
		params = {
			"type": "adlocale",
			"q": query,
			"access_token": access_token
		}

		response = requests.get(base_url, params=params)
		response_json = response.json()

		if "data" in response_json:
			data = response_json["data"]
			for item in data:
				MetaLanguageLocales.objects.get_or_create(name=item["name"], key=item["key"])
				print('saving locale', item["name"], item["key"])
	'''
	for item in language_data:
				MetaLanguageLocales.objects.get_or_create(name=item["name"], key=item["key"])
				print('saving locale', item["name"], item["key"])

	return language_data

