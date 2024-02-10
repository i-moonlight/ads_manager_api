import requests, os, sys, traceback
from django.conf import settings

def slack_alert_api_issue(issue):
	print('SLACK ALERT API ISSUE')
	#print(issue)
	try:
		SLACK_WEBHOOK_API_NOTI =  getattr(settings, 'SLACK_WEBHOOK_API_NOTI')
		if SLACK_WEBHOOK_API_NOTI:
			payload_json = {'text': issue}
			
			# Send the POST request to the Slack webhook URL
			response = requests.post(SLACK_WEBHOOK_API_NOTI, json=payload_json)

			# Check the response status
			if response.status_code == 200:
				print("Message sent successfully")
			else:
				print("Failed to send message:", response.text)
		return True
			
	except Exception as e:
		print(e)
		traceback.print_exc()  # Print the traceback information
		return True
	

def slack_alert_new_user(login_type):
	try:
		SLACK_WEBHOOK_NEW_USER =  os.getenv('SLACK_WEBHOOK_NEW_USER', None)
		if SLACK_WEBHOOK_NEW_USER:
			payload_json = {'text': login_type}
			
			# Send the POST request to the Slack webhook URL
			response = requests.post(SLACK_WEBHOOK_NEW_USER, json=payload_json)

			# Check the response status
			if response.status_code == 200:
				print("Message sent successfully")
			else:
				print("Failed to send message:", response.text)
		return True
			
	except Exception as e:
		print(e)
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
		print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
		return True
	
