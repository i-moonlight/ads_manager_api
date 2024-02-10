from PIL import Image
import requests
from io import BytesIO
from datetime import datetime

from urllib.parse import urlparse
import uuid
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from api.media_library.models import Media
from api.ad_accounts.models import Authorizations
from api.ad_manager.models import (
    Campaigns,
    CampaignsPlatforms,
    AdSets,
    AdSetsPlatforms,
    Ads,
    AdsPlatforms,
    AdsPerformance,
    AdSetsLocations,
    AdSetsJobTitles
)
from linkedin_api.clients.restli.client import RestliClient
from bs4 import BeautifulSoup

import traceback
from core.utils.slack import slack_alert_api_issue

def import_linkedin_account_data(account_id, user_id):
    print("START IMPORT LINKEDIN ACCOUNT DATA")

    try:
        # Get the authorization object
        authorization = Authorizations.objects.filter(
            user=user_id, ad_platform='linkedin'
        ).first()

        if authorization:
            # Set import_start_date_time
            authorization.import_start_date_time = datetime.now()

            access_token = authorization.access_token

            publisher_platform = "linkedin"

            restli_client = RestliClient()

            response = restli_client.finder(
                resource_path="/adCampaignGroupsV2",
                finder_name="search",
                query_params={
                    "search": {
                        "account": {"values": [f"urn:li:sponsoredAccount:{account_id}"]}
                    }
                },
                access_token=access_token,
            )

            campaigns_data = response.elements or []

            for campaign_data in campaigns_data:
                # Convert timestamps to datetime objects
                # Divide by 1000 to convert milliseconds to seconds
                runSchedule_start = campaign_data.get("runSchedule", {}).get("start")

                if runSchedule_start:
                    start_date = datetime.fromtimestamp(
                        runSchedule_start / 1000
                    ).strftime("%Y-%m-%d")
                else:
                    start_date = None

                runSchedule_end = campaign_data.get("runSchedule", {}).get("end")

                if runSchedule_end:
                    end_date = datetime.fromtimestamp(runSchedule_end / 1000).strftime(
                        "%Y-%m-%d"
                    )
                else:
                    end_date = None

                changeAuditStamps_created = (
                    campaign_data.get("changeAuditStamps", {})
                    .get("created", {})
                    .get("time")
                )

                if changeAuditStamps_created:
                    created_date = datetime.fromtimestamp(
                        changeAuditStamps_created / 1000
                    ).strftime("%Y-%m-%d")
                else:
                    created_date = None

                status = campaign_data.get("status")
                api_id = campaign_data.get('id')

                campaign, created = Campaigns.objects.get_or_create(
                    user=user_id,
                    campaigns_platform__ad_platform='linkedin',
                    campaigns_platform__publisher_platform=publisher_platform,
                    defaults={
                        "name": campaign_data.get("name"),
                        "budget": campaign_data.get("totalBudget", {}).get("amount"),
                        "start_date": start_date,
                        "end_date": end_date,
                        "created": created_date,
                        "status": status,
                    },
                )

                if created:
                    CampaignsPlatforms.objects.create(
                        campaign=campaign,
                        ad_platform='linkedin',
                        publisher_platform=publisher_platform,
                        api_id=api_id,
                        disabled=status == "PAUSED",
                        status=status,
                    )
                else:
                    campaign.is_deleted = False
                    campaign.save()

                response = restli_client.finder(
                    resource_path="/adCampaignsV2",
                    finder_name="search",
                    query_params={
                        "search": {
                            "campaignGroup": {
                                "values": [
                                    f'urn:li:sponsoredCampaignGroup:{api_id}'
                                ]
                            }
                        }
                    },
                    access_token=access_token,
                )

                ad_sets_data = response.elements or []

                for ad_set_data in ad_sets_data:
                    changeAuditStamps_created = (
                        ad_set_data.get("changeAuditStamps", {})
                        .get("created", {})
                        .get("time")
                    )

                    if changeAuditStamps_created:
                        created_date = datetime.fromtimestamp(
                            changeAuditStamps_created / 1000
                        ).strftime("%Y-%m-%d")
                    else:
                        created_date = None

                    status = ad_set_data.get("status")
                    api_id = ad_set_data.get('id')

                    ad_set, created = AdSets.objects.get_or_create(
                        campaign=campaign,
                        user=user_id,
                        ad_sets_platform__ad_platform='linkedin',
                        ad_sets_platform__publisher_platform=publisher_platform,
                        defaults={
                            'name': ad_set_data.get("name"),
                            'daily_budget': ad_set_data.get("dailyBudget", {}).get("amount"),
                            'created': created_date,
                            'status': status,
                        }
                    )

                    if created:
                        AdSetsPlatforms.objects.create(
                            ad_set=ad_set,
                            ad_platform='linkedin',
                            publisher_platform=publisher_platform,
                            api_id=api_id,
                            disabled=status == "PAUSED",
                            status=status,
                        )

                        locations = []

                        for l in ad_set_data["targetingCriteria"]["include"]["and"]:
                            if l['or'].get('urn:li:adTargetingFacet:locations'):
                                locations = list(
                                    map(
                                        lambda l: l.split(":")[-1],
                                        l["or"][
                                            "urn:li:adTargetingFacet:locations"
                                        ],
                                    )
                                )
                                break

                        for location in locations:
                            response = restli_client.get(
                                resource_path="/geo/{id}",
                                path_keys={"id": location},
                                access_token=access_token,
                            )

                            AdSetsLocations.objects.create(
                                ad_set=ad_set,
                                location=response.entity["defaultLocalizedName"]['value'],
                            )

                        titles = []

                        for t in ad_set_data["targetingCriteria"]["include"]["and"]:
                            if t['or'].get('urn:li:adTargetingFacet:titles'):
                                titles = list(
                                    map(
                                        lambda t: t.split(":")[-1],
                                        t["or"][
                                            "urn:li:adTargetingFacet:titles"
                                        ],
                                    )
                                )
                                break

                        for title in titles:
                            response = restli_client.get(
                                resource_path="/titles/{id}",
                                path_keys={"id": title},
                                access_token=access_token,
                            )

                            name = response.entity["name"]["localized"]["en_US"]

                            AdSetsJobTitles.objects.create(ad_set=ad_set, name=name)
                    else:
                        ad_set.is_deleted = False
                        ad_set.save()

                    response = restli_client.finder(
                        resource_path="/adCreativesV2",
                        finder_name="search",
                        query_params={
                            "search": {
                                "campaign": {
                                    "values": [
                                        f'urn:li:sponsoredCampaign:{api_id}'
                                    ]
                                }
                            }
                        },
                        access_token=access_token,
                    )

                    ads_data = response.elements or []

                    for ad_data in ads_data:
                        name = restli_client.get(
                            resource_path="/adDirectSponsoredContents/{contentReference}",
                            path_keys={"contentReference": ad_data.get("reference")},
                            query_params={"fields": "name"},
                            access_token=access_token,
                        ).entity["name"]

                        changeAuditStamps_created = (
                            ad_data.get("changeAuditStamps", {})
                            .get("created", {})
                            .get("time")
                        )

                        if changeAuditStamps_created:
                            created_date = datetime.fromtimestamp(
                                changeAuditStamps_created / 1000
                            ).strftime("%Y-%m-%d")
                        else:
                            created_date = None


                        status = ad_data.get("status")
                        api_id = ad_data.get('id')

                        url = f'https://www.linkedin.com/ad-library/detail/{api_id}'
                        result = requests.get(url)
                        doc = BeautifulSoup(result.text, "html.parser")

                        durl = doc.find(
                            attrs={
                                "data-tracking-control-name": "ad_library_ad_preview_content_image"
                            }
                        ).get("href").split('?')
                        qp = '&'.join(list(filter(lambda p: 'trk=' not in p, durl[1].split('&'))))

                        destination_url = f'{durl[0]}?{qp}' if qp else durl[0]

                        call_to_action_linkedin = doc.find(
                            attrs={
                                "data-tracking-control-name": "ad_library_ad_detail_cta"
                            }
                        ).text.strip()
                        headline_content = doc.find(
                            attrs={
                                "data-tracking-control-name": "ad_library_ad_preview_headline_content"
                            }
                        ).find("header")
                        headline = headline_content.find("h2").text.strip()
                        primary_text = description = headline_content.find(
                            "p"
                        ).text.strip()

                        ad, created = Ads.objects.get_or_create(
                            campaign=campaign,
                            ad_set=ad_set,
                            user=user_id,
                            ads_platform__ad_platform='linkedin',
                            ads_platform__publisher_platform=publisher_platform,
                            defaults={
                                'name': name,
                                'destination_url': destination_url,
                                'call_to_action_linkedin': call_to_action_linkedin,
                                'headline': headline,
                                'primary_text': primary_text,
                                'description': description,
                                'created': created_date,
                                'status': status
                            }
                        )

                        if created:
                            image_url = doc.find(
                                class_="ad-preview__dynamic-dimensions-image"
                            ).get("data-delayed-url")

                            if image_url:
                                process_image(ad.id, image_url, user_id)

                            AdsPlatforms.objects.create(
                                ad=ad,
                                ad_platform='linkedin',
                                publisher_platform=publisher_platform,
                                api_id=api_id,
                                disabled=status == "PAUSED",
                                status=status,
                                run_on=True,
                            )

                            response = restli_client.finder(
                                resource_path="/adAnalytics",
                                finder_name="analytics",
                                query_params={
                                    "pivot": "CREATIVE",
                                    "timeGranularity": "DAILY",
                                    "dateRange": {
                                        "start": {
                                            "year": 2021,
                                            "month": 10,
                                            "day": 6,
                                        }
                                    },
                                    "creatives": [f'urn:li:sponsoredCreative:{api_id}'],
                                    "fields": "clicks,impressions,costInUsd,dateRange",
                                },
                                access_token=access_token,
                                version_string='202308'
                            )

                            ads_performance_data = response.elements or []

                            for ad_performance_data in ads_performance_data:
                                impressions = ad_performance_data.get("impressions")
                                clicks = ad_performance_data.get("clicks")
                                spend = float(ad_performance_data.get("costInUsd"))
                                dateRange = ad_performance_data.get("dateRange").get("start")
                                date = f"{dateRange['year']}-{dateRange['month']}-{dateRange['day']}"

                                AdsPerformance.objects.create(
                                    ad=ad,
                                    ad_platform='linkedin',
                                    publisher_platform=publisher_platform,
                                    impressions=impressions,
                                    clicks=clicks,
                                    spend=spend,
                                    date=date,
                                    status=status,
                                    disabled=status == "PAUSED",
                                )
                        else:
                            ad.is_deleted = False
                            ad.save()

            # Set import_end_date_time and is_imported
            authorization.import_end_date_time = datetime.now()
            authorization.is_imported = True

            # Save the updated authorization object
            authorization.save()

            return {
                "message": "Linkedin Ads Data Imported Successfully",
                "ad_platform": 'linkedin',
                "is_importing": False,
            }
        else:
            return {
                "message": f'Authorization not found for user_id and ad_platform=linkedin',
                "ad_platform": 'linkedin',
                "is_importing": False,
            }
    except Exception as e:
        # Handle any other exceptions here
        print(e)
        return {
            "message": f"Error: {str(e)}",
            "ad_platform": 'linkedin',
            "is_importing": False,
        }


def process_image(ad_id, image_url, user_id):
    try:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))

        # Get image details
        width, height = img.size
        file_type = img.format
        file_name = urlparse(image_url).path.split("/")[-1]
        original_file_name = file_name
        mime_type = Image.MIME.get(file_type)  # Get MIME type
        print(mime_type)

        # Create a thumbnail
        thumbnail = img.copy()
        thumbnail.thumbnail((300, 300))

        # Generate a UUID for the thumbnail file name
        thumbnail_uuid = str(uuid.uuid4())
        thumbnail_file_name = (
            f'thumbs/{thumbnail_uuid}{file_name[file_name.rfind("."):]}'
        )

        display_file_name = f"{width}x{height}.{file_type.lower()}"
        # Save the image and thumbnail to S3
        with BytesIO() as output:
            thumbnail.save(output, format=file_type)
            output.seek(0)
            thumbnail_file = ContentFile(output.getvalue())
            actual_thumb_name = default_storage.save(
                thumbnail_file_name, thumbnail_file
            )

        with BytesIO() as output:
            img.save(output, format=file_type)
            output.seek(0)
            image_file = ContentFile(output.getvalue())
            actual_file_name = default_storage.save(
                f"media_files/{file_name}", image_file
            )

        # user = User.objects.get(user=user_id)
        media = Media(
            user=user_id,
            file=actual_file_name,
            file_type=file_type,
            original_file_name=original_file_name,
            display_file_name=display_file_name,
            height=height,
            width=width,
            source="linkedin",
            size=len(response.content),
        )
        media.save()

        # Save the thumbnail file name to the 'thumbnail' column in ads_manager_ads table
        ad = Ads.objects.get(id=ad_id)
        ad.thumbnail = actual_thumb_name
        ad.save()

        print(width, height, file_type, file_name)

        return width, height, file_type, file_name
    except Exception as e:
        print("Error", e)
        traceback.print_exc()  # Print the traceback information
        slack_alert_api_issue(
            traceback.format_exc()
        )  # Send a slack alert for the API issue.
