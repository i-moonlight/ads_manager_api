import requests
import os

def send_notif(task):
	requests.post(f'{os.environ.get("API_SERVER")}/api/ad_manager/notif/', json=task.result)