from django.core.management.base import BaseCommand
from api.ad_accounts.models import Authorizations
from ad_manager.models import Campaigns
from tiktok.models import TikTokCampaigns, TikTokCampaignsPerformance
from django.db.models import Max
from datetime import datetime, timedelta
import traceback
import requests


class Command(BaseCommand):
    help = 'this job is responsible to import titkok campaigns data'

    def get_campaigns(self, integration_obj):
        try:
            url = 'https://business-api.tiktok.com/open_api/v1.3/campaign/get/'
            page = 1
            params = {
                'advertiser_id': integration_obj.account_id,
                'page_size': 1000,
                'page': page,
                'fields': ["campaign_name","budget","create_time","operation_status","objective_type"]
            }
            headers = {
                'Access-Token': integration_obj.access_token
            }
            resp = requests.get(url, headers=headers, params=params)
            campaign_data = []
            if resp.status_code == 200:
                resp = resp.json()['data']
                if resp['page_info']['total_number'] != 0:
                    campaign_data = resp['list']
                    # increment the page
                    page += 1
                    # get the total number of pages exists
                    total_pages = resp['page_info']['total_page']
                    while page <= total_pages:
                        params['page'] = page
                        resp = requests.get(url, headers=headers, params=params)
                        if resp.status_code == 200:
                            resp = resp.json()['data']
                            if resp['page_info']['total_number'] != 0:
                                campaign_data += resp['list']
                                # increment the page again
                                page += 1
                            else:
                                break
                        else:
                            break
                else:
                    self.stdout.write(self.style.WARNING(f'Account id: {integration_obj.account_id} have no campaigns.'))
            else:
                traceback.format_exc()
            
            return campaign_data
        except:
            traceback.format_exc()
            return []

    def save_campaign_performance_data(self, integration_obj, campaign_obj, campaign_id, tiktok_campaign_obj):
        # we should retrieve the max date from TikTokCampaignsPerformance table
        max_date = TikTokCampaignsPerformance.objects.filter(
            campaign__pk=campaign_obj.id,
            tiktok_campaign__pk=tiktok_campaign_obj.id
        ).aggregate(Max('date'))['date__max']
        if max_date is not None:
            start_date = (max_date - timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = max_date.strftime('%Y-%m-%d')
        else:
            start_date = (datetime.now().date() - timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = datetime.now().date().strftime('%Y-%m-%d')
        # here we should make a call to campaign api and get the performance data
        url = 'https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/'
        params = {
            'advertiser_id': integration_obj.account_id,
            'service_type': 'AUCTION',
            'report_type': 'BASIC',
            'data_level': 'AUCTION_CAMPAIGN',
            'dimensions': ["campaign_id"],
            'metrics': ["spend", "impressions", "clicks"],
            'start_date': start_date,
            'end_date': end_date,
            'page_size': 1000,
            'page': 1,
            'filtering': [{"field_name": "campaign_ids", "filter_type": "IN", "filter_value": f"[\"{campaign_id}\"]"}]
        }
        headers = {
            'Access-Token': integration_obj.access_token,
            'Content-Type': 'application/json'
        }
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 200:
            resp = resp.json()['data']
            if resp['page_info']['total_number'] != 0:
                campaign_metrics = resp['list'][0]['metrics']
                TikTokCampaignsPerformance.objects.get_or_create(
                    campaign=campaign_obj,
                    tiktok_campaign=tiktok_campaign_obj,
                    date=datetime.strptime(end_date, '%Y-%m-%d'),
                    defaults={
                        'impressions': campaign_metrics['impressions'],
                        'clicks': campaign_metrics['clicks'],
                        'spend': campaign_metrics['spend'],
                    }
                )

    def save_campaigns(self, integration_obj, campaign_list):
        for campaign in campaign_list:
            campaign_obj, _ = Campaigns.objects.get_or_create(
                user=integration_obj.user,
                name=campaign['campaign_name'],
                defaults={
                    'budget': campaign['budget'],
                    'start_date': str(campaign['create_time']).split(' ')[0],
                    'status': campaign['operation_status']
                }
            )
            tiktok_campaign_obj, _ = TikTokCampaigns.objects.get_or_create(
                user=integration_obj.user,
                campaign=campaign_obj,
                tiktok_campaign_id=campaign['campaign_id'],
                defaults={
                    'name': campaign['campaign_name'],
                    'objective': campaign['objective_type'],
                    'status': campaign['operation_status']
                }
            )
            self.save_campaign_performance_data(integration_obj, campaign_obj, int(campaign['campaign_id']), tiktok_campaign_obj)

    def handle(self, *args, **kwargs):
        try:
            # get all tiktok integrations users from Authorizations
            integrations = Authorizations.objects.filter(ad_platform='tiktok')
            for integration in integrations:
                # here we need to get and save the campaigns
                campaigns = self.get_campaigns(integration)
                if len(campaigns) > 0:
                    self.save_campaigns(integration, campaigns)
        except:
            traceback.format_exception()
