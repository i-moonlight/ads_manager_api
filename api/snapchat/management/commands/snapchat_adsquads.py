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
            ads_url = f'https://adsapi.snapchat.com/v1/adaccounts/{account_id}/adsquads'
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            # get request to Snapchat API to get json object of adsquad data 
            adsquads_data = requests.get(url=ads_url, headers=headers)
            json_data = adsquads_data.json()
            data =  json_data['adsquads']
            for adsquad_data in data:
                adsquad_id = AdSets.objects.create(user=cred.user, campaign=adsquad_data['adsquad']['campaign_id'], name=adsquad_data['adsquad']['name'])
                # creating a new record for snapchat adsquad
                snapchat_adsquad =  SnapchatAdSets.objects.create(user=cred.user, ad=adsquad_id, snapchat_ad=adsquad_data['ad']['name'])

                # retrieve adsquad stats from the Snapchat api (impressions, clicks)
                adsquad_stats_url = f"https://adsapi.snapchat.com/v1/adsquads/{adsquad_data['adsquad']['id']}/stats"
                result_stats = request.get(url=adsquad_stats_url, headers=headers).json().get('total_stats')
                for result in result_stats:
                    SnapchatAdSetsPerformance.objects.create(
                        ad_set=adsquad_id, 
                        snapchat_ad_set=snapchat_adsquad, 
                        impressions=result['total_stat']['stats']['impressions'], 
                        clicks=result['total_stat']['stats']['swipes'], 
                        spend=result['total_stat']['stats']['spend'], 
                        date=result['total_stat']['finalized_data_end_time'])
            self.stdout.write(self.style.SUCCESS('Successfully ran your command'))
            