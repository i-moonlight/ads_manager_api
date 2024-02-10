# -*- coding: utf-8 -*-
#!/usr/bin/env python

from urllib.parse import urlparse

from api.ad_accounts.models import Authorizations

from datetime import datetime

def import_pinterest_account_data(account_id, user_id):
	
	print('IMPORT PINTEREST ACCOUNT DATA')
	try:
	
		authorization = Authorizations.objects.filter(user=user_id,ad_platform='pinterest').first()

		if authorization:
			 # Set import_start_date_time
			authorization.import_start_date_time = datetime.now()
			# Extract the values from the authorization object
			account_id = authorization.account_id
			access_token = authorization.access_token
			refresh_token = authorization.refresh_token
			user_id = authorization.user

			# Import Pinterest Data

			return {
				'message': 'Pinterest Ads Data Imported Successfully',
				'ad_platform': 'pinterest',
				'is_importing': False,
			}
		else:
			return {
				'message': 'Authorization not found for Pinterest',
				'ad_platform': 'pinterest',
				'is_importing': False,
			}
			
	except Exception as e:
        # Handle any other exceptions here
		return {
          'message': f'Error: {str(e)}',
          'ad_platform': 'pinterest',
          'is_importing': False,
        }

	
