from django.core.management.base import BaseCommand
from ad_accounts.models import Authorizations
from ad_manager.models import *
import requests
from snapchat.models import *


class Command(BaseCommand):
    help = 'This command creates a new meta ads campaign'

    def handle(self, args, *options):
        self.get_campaign()

    def get_ads(self, request):
        # retrieve credentials for Snapchat from the authorization  model
        creds = Authorizations.objects.filter(ad_platform='snapchat').values('account_id', 'access_token', 'user')
        for cred in creds:
            account_id = cred['account_id']
            access_token = cred['access_token']
            ads_url = f'https://adsapi.snapchat.com/v1/adaccounts/{account_id}/ads'
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            # get request to Snapchat API to get json object of ad data 
            ads_data = requests.get(url=ads_url, headers=headers)
            json_data = ads_data.json()
            data =  json_data['ads']
            for ads_data in data:
                ad_id = Ads.objects.create(user=cred.user, campaign=None, ad_set=None, name=['ad']['id'])
                # creating a new record for snapchat ad
                snapchat_ad =  SnapchatAds.objects.create(user=cred.user, ad=ad_id, snapchat_ad=ads_data['ad']['name'])

                # retrieve ad stats from the Snapchat api (impressions, clicks)
                ad_stats_url = f"https://adsapi.snapchat.com/v1/ads/{ads_data['ad']['id']}/stats"
                result_stats = request.get(url=ad_stats_url, headers=headers).json().get('total_stats')
                for result in result_stats:
                    SnapchatAdsPerformance.objects.create(
                        ad=ad_id, 
                        snapchat_ad=snapchat_ad , 
                        impressions=result['total_stat']['stats']['impressions'], 
                        clicks=result['total_stat']['stats']['swipes'], 
                        spend=result['total_stat']['stats']['spend'], 
                        date=result['total_stat']['finalized_data_end_time'])


            self.stdout.write(self.style.SUCCESS('Successfully ran your command'))
            