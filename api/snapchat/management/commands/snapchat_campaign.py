from urllib import request
from django.core.management.base import BaseCommand
from api.ad_accounts.models import Authorizations
import requests
from api.ad_manager.models import *
from api.snapchat.models import *
from api.user.models import User

class Command(BaseCommand):
    help = 'This command creates a new meta ads campaign'

    def handle(self, *args, **options):
        self.get_campaign()

    def get_campaign(self):
        # retrieve credentials for Snapchat from the authorization  model
        creds = Authorizations.objects.filter(ad_platform='snapchat').values('account_id', 'access_token', 'user')
        for cred in creds:
            account_id = cred['account_id']
            access_token = cred['access_token']
            # retrieving campaigns id from Snapchat ad_accounts api
            campaigns_url = f'https://adsapi.snapchat.com/v1/adaccounts/{account_id}/campaigns'
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            # get request to Snapchat API to get json objet  of campaign data 
            campaign_data = requests.get(url=campaigns_url, headers=headers)
            json_data = campaign_data.json()
            data = json_data['campaigns']
            for campaign in data:
                campaign_id = Campaigns.objects.create(user=cred.user, name=campaign['campaign']['id'])
                # creating a new record for snapchat campaign
                snap_camp = SnapchatCampaigns.objects.create(
                    user=cred.user,
                    campaign=campaign_id,
                    snapchat_campaign_id=campaign['campaign']['id'],
                    name=campaign['campaign']['name'],
                    status=campaign['campaign']['status'],
                    objective=campaign['campaign']['objective']
                )
                # retrieve campaign stats from the Snapchat api (impressions, clicks)
                campaign_stats_url = f"https://adsapi.snapchat.com/v1/campaigns/{campaign['campaign']['id']}/stats"
                result_stats = request.get(url=campaign_stats_url, headers=headers).json().get('total_stats')
                for result in result_stats:
                    SnapchatCampaignsPerformance.objects.create(
                        campaign=campaign_id,
                        snapchat_campaign=snap_camp,
                        impressions=result['total_stat']['stats']['impressions'],
                        spend=result['total_stat']['stats']['spend'],
                        clicks=result['total_stat']['stats']['swipes'],
                        date=result['total_stat']['finalized_data_end_time']
                    )

            self.stdout.write(self.style.SUCCESS('Successfully ran your command'))

