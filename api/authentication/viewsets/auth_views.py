import base64, json, requests, os, sys

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

import jwt

from rest_framework import viewsets
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from datetime import datetime

from api.authentication.serializers.login import _generate_jwt_token
from api.user.models import User
from api.authentication.models import ActiveSession

from rest_framework.views import APIView
from rest_framework_tracking.mixins import LoggingMixin

from sesame import utils
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
# 
from api.media_library.models import *
from api.ad_manager.models import *
from api.user.models import *
from api.ad_accounts.models import *

from core.utils.slack import slack_alert_new_user


class FacebookSocialLogin(LoggingMixin, APIView):
	def post(self, request):  
		
		try:
			print("FacebookSocialLogin post")

			code = request.data.get("code")
			client_id = getattr(settings, 'META_APP_ID')
			client_secret = getattr(settings, 'META_APP_SECRET')
			redirect_uri = getattr(settings, 'FE_SERVER') + '/login/facebook'

			root_url = 'https://graph.facebook.com/oauth/access_token?'
			params = { 'client_id': client_id, 'client_secret': client_secret, 'code': code, 'redirect_uri': redirect_uri}
			print(params)
			data = requests.get(root_url, params=params)            
			response = data._content.decode('utf-8')
			objJson = json.loads(response)
			print(objJson)
			access_token = objJson['access_token']
			fb_url_me = 'https://graph.facebook.com/me?fields=id,first_name,middle_name,last_name,name,email'
			headers_api = {
				'Authorization': 'Bearer ' + access_token
			}
			data_me = requests.get(url=fb_url_me, headers=headers_api)
			response_me = data_me._content.decode('utf-8')
			objJson = json.loads(response_me)            
			
			provider_id = objJson['id']
			provider = 'facebook'
				
			try:
				user = User.objects.get(provider=provider, provider_id=provider_id)
				
			except User.DoesNotExist:
				
				first_name = objJson['first_name'] 
				last_name = objJson['last_name'] 
				display_name = first_name + ' ' + last_name
				user = User()
				user.email = objJson['email']   
				user.first_name = first_name
				user.last_name = last_name
				user.display_name = display_name
				user.password = make_password(BaseUserManager().make_random_password())
				user.extra_data = json.dumps(objJson)
				user.provider = provider
				user.provider_id = provider_id
				user.save()
				slack_alert_new_user('Facebook Login')
			try:
				session = ActiveSession.objects.get(user=user)
				if not session.token:
					raise ValueError

				jwt.decode(session.token, settings.SECRET_KEY, algorithms=["HS256"])

			except (ObjectDoesNotExist, ValueError, jwt.ExpiredSignatureError):
				session = ActiveSession.objects.create(
					user=user, token=_generate_jwt_token(user)
				)
			
			return Response({
				"success": True,
				"token": session.token,
				"access": session.token,
				"user": {"_id": user.pk, "username": user.username, "display_name": user.display_name, "email": user.email, "created": user.date},
			})
		
		except Exception as e:
			print(e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)

	def get(self, request):
		print("FacebookSocialLogin get")
		

class GoogleSocialLogin(LoggingMixin, APIView):
	def post(self, request):  
		
		try:
			print("GoogleSocialLogin A")


			code = request.data.get("code")
			client_id = getattr(settings, 'GOOGLE_CLIENT_ID')
			client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET')
			redirect_uri = getattr(settings, 'FE_SERVER') + '/login/google'

			root_url = 'https://oauth2.googleapis.com/token?'
			params = { 'client_id': client_id, 'client_secret': client_secret, 'code': code, 'redirect_uri': redirect_uri, 'grant_type': 'authorization_code'}
			print(params)
			data = requests.post(root_url, params=params)    
			print(data)
			print(data.text)        
			response = data._content.decode('utf-8')
			objJson = json.loads(response)
			print(objJson)
			access_token = objJson['access_token']

			payload = {'access_token': access_token}  # validate the token
			print("GoogleSocialLogin B")
			print(payload)
			r = requests.get(
				'https://www.googleapis.com/oauth2/v2/userinfo', params=payload)
			objJson = json.loads(r.text)

			print(objJson)
			print("GoogleSocialLogin_C")

			if 'error' in objJson:
				print("GoogleSocialLogin_D")
				content = {
					'message': 'wrong google token / this google token is already expired.'}
				return Response(content)
			
			print("GoogleSocialLogin_E")
			provider_id = objJson["id"]
			provider = 'google'
			
			print("GoogleSocialLogin_provider_id: ", provider_id)

			try:
				print('GoogleSocialLogin_Check_User')
				user = User.objects.get(provider=provider, provider_id=provider_id)
				#print("GoogleSocialLogin_Check_User")
			except User.DoesNotExist:
				#print("GoogleView_User_DoesNotExist")            
				# 
				
				first_name = objJson['given_name']
				last_name = objJson['family_name']
				display_name = first_name + ' ' + last_name
				user = User()
				#user.username = email
				user.email = objJson["email"]
				user.first_name = first_name
				user.last_name = last_name
				user.display_name = display_name
				user.password = make_password(BaseUserManager().make_random_password())
				user.extra_data = json.dumps(objJson)
				user.provider = provider
				user.provider_id = provider_id
				user.save()
				slack_alert_new_user('Google Login')
			try:
				session = ActiveSession.objects.get(user=user)
				if not session.token:
					raise ValueError

				jwt.decode(session.token, settings.SECRET_KEY, algorithms=["HS256"])

			except (ObjectDoesNotExist, ValueError, jwt.ExpiredSignatureError):
				session = ActiveSession.objects.create(
					user=user, token=_generate_jwt_token(user)
				)

			return Response({
				"success": True,
				"token": session.token,
				"access": session.token,
				"user": {"_id": user.pk, "username": user.username, "display_name": user.display_name, "email": user.email, "created": user.date},
			})
		
		except Exception as e:
			print(e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)


class LinkedInSocialLogin(LoggingMixin, APIView):
	def post(self, request):  
		try:
			print("LinkedInSocialLogin")
			code = request.data.get("code")
			client_id = getattr(settings, 'LINKEDIN_OAUTH_CLIENT_ID')
			client_secret = getattr(settings, 'LINKEDIN_OAUTH_CLIENT_SECRET')
			redirect_uri = getattr(settings, 'FE_SERVER') + '/login/linkedin'
			root_url = 'https://www.linkedin.com/oauth/v2/accessToken'
			
			params = { 'client_id': client_id, 'client_secret': client_secret, 'code': code, 'grant_type': 'authorization_code', 'redirect_uri': redirect_uri}
			
			print(params)
			data = requests.post(root_url, params=params, headers={
			'Content-Type': 'application/x-www-form-urlencoded',
			})
			
			response = data._content.decode('utf-8')
			print(response)
			objJson = json.loads(response)
			
			access_token = objJson['access_token']
			
			linkedin_url_me = 'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))'
			headers_api = {
				'Authorization': 'Bearer ' + access_token
			}
			data_me = requests.get(url=linkedin_url_me, headers=headers_api)
			response_me = data_me._content.decode('utf-8')
			objJson = json.loads(response_me)
			email = objJson['elements'][0]['handle~']['emailAddress']
			
			data_me_1 = requests.get(url='https://api.linkedin.com/v2/me', headers=headers_api)
			response_me_1 = data_me_1._content.decode('utf-8')
			objJson_1 = json.loads(response_me_1) 
			provider_id = objJson_1['id']
			provider = 'linkedin'
			
			try:
				user = User.objects.get(provider=provider, provider_id=provider_id)
				#print("LinkedInSocialLogin_Check_User exists")
				user.last_login = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
				user.save()
			except User.DoesNotExist:
				#print("LinkedInSocialLogin_Check_User does not exists.  Create new user")        
				
				first_name = objJson_1['localizedFirstName']
				last_name = objJson_1['localizedLastName']
				display_name = first_name + ' ' + last_name
				user = User()
				#user.username = email
				user.email = email
				user.first_name = first_name
				user.last_name = last_name
				user.display_name = display_name
				user.password = make_password(BaseUserManager().make_random_password())
				user.extra_data = json.dumps(objJson_1)
				user.provider = provider
				user.provider_id = provider_id
				user.save()	
				slack_alert_new_user('LinkedIn Login')			
			try:
				session = ActiveSession.objects.get(user=user)
				if not session.token:
					raise ValueError

				jwt.decode(session.token, settings.SECRET_KEY, algorithms=["HS256"])

			except (ObjectDoesNotExist, ValueError, jwt.ExpiredSignatureError):
				session = ActiveSession.objects.create(
					user=user, token=_generate_jwt_token(user)
				)
				
			return Response({
				"success": True,
				"token": session.token,
				"user": {"_id": user.pk, "username": user.username, "display_name": user.display_name, "email": user.email, "created": user.date},
			})
			
		except Exception as e:
			print(e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
	

class PinterestSocialLogin(LoggingMixin, APIView):
	def post(self, request):  
		try:
			print("PinterestSocialLogin")
			code = request.data.get("code")
			client_id = getattr(settings, 'PINTEREST_OAUTH_CLIENT_ID')
			client_secret = getattr(settings, 'PINTEREST_OAUTH_CLIENT_SECRET')
			redirect_uri = getattr(settings, 'FE_SERVER') + '/login/pinterest'
			root_url = 'https://api.pinterest.com/v5/oauth/token'
			params = {'code': code, 'grant_type': 'authorization_code', 'redirect_uri': redirect_uri}
			data_string = f'{client_id}:{client_secret}'
			b64encoded = base64.b64encode(data_string.encode())
			headers_api = {
				'Content-Type': 'application/x-www-form-urlencoded',
				'Authorization': 'Basic ' + b64encoded.decode('utf-8')
			}
			data = requests.post(root_url, data=params, headers=headers_api)
			response = data._content.decode('utf-8')
			objJson = json.loads(response)
			access_token = objJson['access_token']
			# 
			pinterest_url_me = 'https://api.pinterest.com/v5/user_account'
			headers_api = {
				'Authorization': 'Bearer ' + access_token
			}
			data_me = requests.get(url=pinterest_url_me, headers=headers_api)
			response_me = data_me._content.decode('utf-8')
			objJson = json.loads(response_me)

			provider_id = objJson['username']  
			provider = 'pinterest'
			
			try:
				user = User.objects.get(provider=provider, provider_id=provider_id)
				#print("PinterestSocialLogin_Check_User exists")
				user.last_login = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
				user.save()
				#print("Update pinterest successfully")
			except User.DoesNotExist:
				
				user = User()
				#user.username = email
				#user.email = email
				#user.first_name = first_name
				#user.last_name = last_name
				user.display_name = objJson['username']  
				user.password = make_password(BaseUserManager().make_random_password())
				user.extra_data = json.dumps(objJson)
				user.provider = provider
				user.provider_id = provider_id
				user.save()
				slack_alert_new_user('Pinterest Login')				
			try:
				session = ActiveSession.objects.get(user=user)
				if not session.token:
					raise ValueError

				jwt.decode(session.token, settings.SECRET_KEY, algorithms=["HS256"])

			except (ObjectDoesNotExist, ValueError, jwt.ExpiredSignatureError):
				session = ActiveSession.objects.create(
					user=user, token=_generate_jwt_token(user)
				)
				
			return Response({
				"success": True,
				"token": session.token,
				"user": {"_id": user.pk, "username": user.username, "display_name": user.display_name, "email": user.email, "created": user.date},
			})
			
		except Exception as e:
			print(e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)


class SnapchatSocialLogin(LoggingMixin, APIView):
	def post(self, request):  
		try:
			print("SnapchatSocialLogin")
			code = request.data.get("code")
			state = request.data.get("state")
			# print("GetTokenFromSnapchatView_code: ", state)
			client_id = getattr(settings, 'SNAPCHAT_OAUTH_CLIENT_ID')
			client_secret = getattr(settings, 'SNAPCHAT_OAUTH_CLIENT_SECRET')
			redirect_uri = getattr(settings, 'FE_SERVER') + '/login/snapchat'

			root_url = 'https://accounts.snapchat.com/accounts/oauth2/token'
			# code_verifier = str(pkce.generate_code_verifier(length=128))
			# code_challenge = pkce.get_code_challenge(code_verifier)
			params = {'client_id': client_id, 'redirect_uri': redirect_uri, 'code': code, 'grant_type': 'authorization_code', 'code_verifier': state}
			data_string = f'{client_id}:{client_secret}'
			b16encoded = base64.b16encode(data_string.encode())
			headers_api = {
				'Content-Type': 'application/x-www-form-urlencoded',
				'Authorization': 'Basic ' + b16encoded.decode('utf-8')
			}
			data = requests.post(root_url, data=params, headers=headers_api)
			response = data._content.decode('utf-8')
			
			objJson = json.loads(response)
			print("GetTokenFromSnapchatView_access_token_data:", objJson)
			access_token = objJson['access_token']
			access_token=access_token.strip()
			# print("GetTokenFromSnapchatView_access_token_data:", access_token)
			snapchat_url_me = 'https://kit.snapchat.com/v1/me'
			headers_api = {
				'Content-Type': 'application/json',
				'Authorization': 'Bearer ' + f'{access_token}'
			}
			jSON_body= {"query":"{me{displayName externalId}}"}
			data_me = requests.post(url=snapchat_url_me, json=jSON_body, headers=headers_api)
			response_me = data_me._content.decode('utf-8')
			objJson = json.loads(response_me)
			
			provider_id = objJson.get('data').get('me').get('externalId')
			provider = 'snapchat'
			
			try:
				user = User.objects.get(provider=provider, provider_id=provider_id)				
				user.last_login = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
				user.save()
			except User.DoesNotExist:
				
				user = User()
				user.display_name = objJson.get('data').get('me').get('displayName')  
				user.password = make_password(BaseUserManager().make_random_password())
				user.extra_data = json.dumps(objJson)
				user.provider = provider
				user.provider_id = provider_id
				user.save()
				slack_alert_new_user('Pinterest Login')		
			try:
				session = ActiveSession.objects.get(user=user)
				if not session.token:
					raise ValueError

				jwt.decode(session.token, settings.SECRET_KEY, algorithms=["HS256"])

			except (ObjectDoesNotExist, ValueError, jwt.ExpiredSignatureError):
				session = ActiveSession.objects.create(
					user=user, token=_generate_jwt_token(user)
				)
				
			return Response({
				"success": True,
				"token": session.token,
				"user": {"_id": user.pk, "username": user.username, "display_name": user.display_name, "email": user.email, "created": user.date},
			})
			
		except Exception as e:
			print(e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)


class TiktokSocialLogin(LoggingMixin, APIView):
	def post(self, request):  
		try:
			print("TiktokSocialLogin")
			code = request.data.get("code")
			#print("GetTokenFromTiktokView_code: ", code)
			client_key = getattr(settings, 'TIKTOK_OAUTH_CLIENT_KEY')
			client_secret = getattr(settings, 'TIKTOK_OAUTH_CLIENT_SECRET')
			
			root_url = 'https://open-api.tiktok.com/oauth/access_token/'
			params = { 'client_key': client_key, 'client_secret': client_secret, 'code': code, 'grant_type': 'authorization_code'}
			data = requests.post(root_url, params=params)
			response = data._content.decode('utf-8')

			print(response)
			objJson = json.loads(response)
			
			access_token = objJson['data']['access_token']
			# print("GetTokenFromTiktokView_access_token: ", access_token)
			# 
			tiktok_url_me = 'https://open.tiktokapis.com/v2/user/info/?fields=display_name,follower_count,open_id,union_id,avatar_url'
			headers_api = {
				'Authorization': 'Bearer ' + access_token
			}
			data_me = requests.get(url=tiktok_url_me, headers=headers_api)
			response_me = data_me._content.decode('utf-8')
			objJson = json.loads(response_me)
			
			provider_id = objJson['data']['user']['union_id']
			provider = 'tiktok'
			
			try:
				user = User.objects.get(provider=provider, provider_id=provider_id)				
				user.last_login = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
				user.save()
			except User.DoesNotExist:
				
				user = User()
				user.display_name = objJson['data']['user']['display_name']
				user.password = make_password(BaseUserManager().make_random_password())
				user.extra_data = json.dumps(objJson)
				user.provider = provider
				user.provider_id = provider_id
				user.save()		
				slack_alert_new_user('TikTok Login')		
			try:
				session = ActiveSession.objects.get(user=user)
				if not session.token:
					raise ValueError

				jwt.decode(session.token, settings.SECRET_KEY, algorithms=["HS256"])

			except (ObjectDoesNotExist, ValueError, jwt.ExpiredSignatureError):
				session = ActiveSession.objects.create(
					user=user, token=_generate_jwt_token(user)
				)
				
			return Response({
				"success": True,
				"token": session.token,
				"user": {"_id": user.pk, "username": user.username, "display_name": user.display_name, "email": user.email, "created": user.date},
			})
			
		except Exception as e:
			print(e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)


class GetSecureLoginLink(LoggingMixin, APIView):
	def post(self, request):  
		
		print("Get Secure Login Link")
		email = request.data.get("email")
		try:
			user = User.objects.get(email=email, provider=None)
			token_sesame = utils.get_token(user)

			link_active = settings.FE_SERVER + '/secure_login/' + \
			''.join(str(token_sesame))
			message = render_to_string('api/mail/mail_login_from_email_link.html', {
									'link_active': link_active, 'email': email})
			send = EmailMessage(settings.SECURE_EMAIL_TITLE, message,
								from_email=settings.EMAIL_FROM, to=[email])
			send.content_subtype = 'html'
			send.send()
			return Response({"email": email}, status=status.HTTP_200_OK)    
		except User.DoesNotExist:
			
			user = User()

			user.display_name = email
			# provider random default password
			user.password = make_password(
				BaseUserManager().make_random_password())
			user.email = email
			
			user.save()
			token_sesame = utils.get_token(user)

			link_active = settings.FE_SERVER + '/secure_login/' + \
			''.join(str(token_sesame))
			
			message = render_to_string('api/mail/mail_register_from_email_link.html', {
									'link_active': link_active, 'email': email})
			send = EmailMessage(settings.SECURE_EMAIL_TITLE, message,
								from_email=settings.EMAIL_FROM, to=[email])
			send.content_subtype = 'html'
			send.send()

			slack_alert_new_user('Email Login')

			return Response({"status": 199, "email": email}, status=status.HTTP_200_OK)
		except Exception as e:
			print(e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
		
		
		return Response({"data": "myData"}, status=status.HTTP_400_BAD_REQUEST)


class LoginByEmailLinkMVS(LoggingMixin, viewsets.ModelViewSet):    

	@action(methods=["GET"], detail=False, url_path="secure_login", url_name="secure_login")

	def secure_login(self, request, *args, **kwargs):
		try:
			token_sesame = kwargs['token_sesame']
		

			user = authenticate(
				request,
				sesame=token_sesame,
				scope="",
				max_age=settings.SESAME_MAX_AGE,
			)
			
			if user is None:
				print("Login fail")
				return Response({"message": "Login failed"}, status=status.HTTP_401_UNAUTHORIZED)
			
			user.last_login = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
			user.save()
			
			 # Always create a new session for each login attempt
			session = ActiveSession.objects.create(
				user=user, token=_generate_jwt_token(user)
			)
				
			return Response({
				"success": True,
				"token": session.token,
				"user": {"_id": user.pk, "username": user.username, "display_name": user.display_name, "email": user.email, "created": user.date},
			})
			
		except Exception as e:
			print(e)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
			print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)


class ManagerAccountMVS(viewsets.ModelViewSet):
	permission_classes = [IsAuthenticated,]

	@action(methods=["DELETE"], detail=False, url_path="delete_account", url_name="delete_account")
	def delete_account(self, request, *args, **kwargs):
		try:
			user_id = request.user.id
			# print("ManagerAccountMVS_delete_account: ", user_id)
			# api_ad_manager
			AdsPlatforms.objects.filter(ad__user_id=user_id).delete()
			AdsPerformance.objects.filter(ad__user_id=user_id).delete()
			Ads.objects.filter(user_id=user_id).delete()
			# 
			AdSetsKeywords.objects.filter(ad_set__user_id=user_id).delete()
			AdSetsLanguages.objects.filter(ad_set__user_id=user_id).delete()
			AdSetsLocations.objects.filter(ad_set__user_id=user_id).delete()
			AdSetsPlatforms.objects.filter(ad_set__user_id=user_id).delete()
			AdSetsPerformance.objects.filter(ad_set__user_id=user_id).delete()
			AdSets.objects.filter(user_id=user_id).delete()
			# 
			CampaignsPlatforms.objects.filter(campaign__user_id=user_id).delete()
			CampaignsPerformance.objects.filter(campaign__user_id=user_id).delete()
			Campaigns.objects.filter(user_id=user_id).delete()

			# api_media_library
			Media.objects.filter(user_id=user_id).delete()

			# api_ad_accounts
			Authorizations.objects.filter(user_id=user_id).delete()

			# api_authentication
			ActiveSession.objects.filter(user_id=user_id).delete()

			# api_user
			# User.objects.filter(id=user_id).delete()

			data = {}
			data['message'] = 'Delete successfully!'
			return Response(data, status=status.HTTP_204_NO_CONTENT)
			# return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)			
		except Exception as error:
			print("ManagerAccountMVS_delete_account: ", error)
		return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)