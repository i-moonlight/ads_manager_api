from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin
from django.template import loader
import requests
import os

import sys
from ..ad_accounts.models import Authorizations
from .models import *
from datetime import datetime, timedelta
import base64


client_id = getattr(settings, 'PINTEREST_OAUTH_CLIENT_ID')
client_secret = getattr(settings, 'PINTEREST_OAUTH_CLIENT_SECRET')


class Enable(LoggingMixin, APIView):
	def get(self, request):
		Authorizations.objects.filter(
			user=request.user, ad_platform='pinterest').delete()
		
		redirect_uri = getattr(settings, 'FE_SERVER') + '/ad-accounts'
		authorization_url = 'https://www.pinterest.com/oauth/?client_id=' + client_id   + '&redirect_uri=' + redirect_uri + '&response_type=code&scope=ads:read,ads:write,boards:read,boards:write,pins:read,pins:write,user_accounts:read&grant_typeauthorization_code'

		return Response({"authorization_url": authorization_url})


class DisableAPI(LoggingMixin, APIView):
	def delete(self, request):
		Authorizations.objects.filter(
			user=request.user, ad_platform='pinterest').delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


class Oauth(LoggingMixin, APIView):
	def post(self, request):
		code = request.data.get("code")
		code = str(code)
		# Get Access token

		redirect_uri = getattr(settings, 'FE_SERVER') + '/ad-accounts'

		access_token_url = 'https://api.pinterest.com/v5/oauth/token?'

		payload = {
			'grant_type' : 'authorization_code',
			'code' : code ,
			'redirect_uri' : redirect_uri,
		}

		base64_auth = client_id + ':' + client_secret
		base64_auth = base64_auth.encode('ascii')
		base64_auth = base64.b64encode(base64_auth)
		base64_auth = base64_auth.decode('ascii')

		headers = {
        	"Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
			"Authorization" : "Basic " + base64_auth,
    	}

		response = requests.post(url=access_token_url, headers=headers, data=payload)
		token_info  = response.json()

		access_token = token_info['access_token']
		expires_in  = token_info['expires_in']
		access_token_expiry = datetime.utcnow() + timedelta(seconds=expires_in) 
		refresh_token = token_info['refresh_token']
		refresh_token_expires_in  = token_info['refresh_token_expires_in']
		refresh_token_expiry = datetime.utcnow() + timedelta(seconds=refresh_token_expires_in) 

		authorization = Authorizations()
		authorization.user = request.user
		authorization.ad_platform = 'pinterest'
		authorization.refresh_token = refresh_token
		authorization.refresh_token_expiry = refresh_token_expiry
		authorization.access_token = access_token
		authorization.access_token_expiry = access_token_expiry
		authorization.save()

		ad_account_details_url = 'https://api.pinterest.com/v5/ad_accounts/'
	
		bearer_token = "Bearer " + str(access_token)
		
		headers = {
			"Authorization": bearer_token,
		}
		response = requests.get(url=ad_account_details_url, headers=headers)
		account_details  = response.json()

		account_ids =  account_details['items']

		accounts=[]
		for i in account_ids:
			account = {}
			account['account_id'] = i['id']
			account['account_name'] = i['name']
			accounts.append(account)

		

		if len(account_ids) == 1:
				account_id = i['id']
				account_name = i['name']
				authorization.account_id = account_id
				authorization.account_name = account_name
				authorization.date_time = datetime.utcnow()
				#authorization.ip_address = "192.168.0.9"
				authorization.save()

		return Response({'accounts': accounts, 'ad_platform': 'pinterest'})


class Boards(LoggingMixin, APIView):
	def get(self,request,format=None):

		try:
			print('Get Pinterest Boards')
			authorization = Authorizations.objects.filter(user=request.user, ad_platform="pinterest").first()
			headers = {
					"Content-Type": "application/json; charset=utf-8",
					"Authorization": "Bearer " + authorization.access_token,
			}

			response = requests.get(
					url="https://api.pinterest.com/v5/boards",
					headers=headers,
			)

			boards_data = response.json()
			boards = []
			for board in boards_data['items']:
				board_item = {}
				board_item['name'] = board['name']
				board_item['id'] = board['id']
				boards.append(board_item)
	
			
			return Response({"boards": boards})
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

	# def get(self,request,format=None):

	# 	try:
	# 		print('Get Pinterest Boards')
			
	# 		boards = [
	# 			{
	# 			"name": "Pinterest Boards Test A",
	# 			"id": "101387855401774"
	# 			},
	# 			{
	# 			"name": "Pinterest Boards Test B",
	# 			"id": "105794688551547"
	# 			},
	# 			{
	# 			"name": "Pinterest Boards Test C",
	# 			"id": "108324801697548"
	# 			},
	# 			{
	# 			"name": "Pinterest Boards Test D",
	# 			"id": "111308081671695"
	# 			},
	# 			{
	# 			"name": "Pinterest Boards Test E",
	# 			"id": "114234645367508"
	# 			},
				
	# 		]
			
	# 		return Response({"boards": boards})
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


	def post(self, request):
				try:
						authorization = Authorizations.objects.filter(user=request.user, ad_platform="pinterest").first()
						headers = {
								"Content-Type": "application/json; charset=utf-8",
								"Authorization": "Bearer " + authorization.access_token,
						}
						board_name = request.data.get("name")
						board_description = request.data.get("description")
						#board_privacy = request.data.get("privacy")
						board_privacy = 'PUBLIC'

						response = requests.post(
								url="https://api.pinterest.com/v5/boards/",
								json={"name": board_name, "description": board_description, "privacy": board_privacy},
								headers=headers,
						)

						board = response.json()

						return Response({"board": board})
				except Exception as e:
						print(e)
	
