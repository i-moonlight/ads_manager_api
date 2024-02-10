from django.urls import path

from .views import *

# Campaigns
campaign_get_by_id_and_user_api = CampaignsMVS.as_view({
    'get': 'campaign_get_by_id_and_user_api'
})
campaigns_basic_get_all_by_user_api = CampaignsMVS.as_view({
    'get': 'campaigns_basic_get_all_by_user_api'
})
campaigns_get_all_by_user_api = CampaignsMVS.as_view({
    'get': 'campaigns_get_all_by_user_api'
})
campaigns_get_all_by_user_1_api = CampaignsMVS.as_view({
    'get': 'campaigns_get_all_by_user_1_api'
})
campaigns_get_all_by_user_id_api = CampaignsMVS.as_view({
    'get': 'campaigns_get_all_by_user_id_api'
})
campaigns_ungroup_get_all_by_user_api = CampaignsMVS.as_view({
    'get': 'campaigns_ungroup_get_all_by_user_api'
})
campaigns_filter_all_by_user_and_start_end_date_api = CampaignsMVS.as_view({
    'get': 'campaigns_filter_all_by_user_and_start_end_date_api'
})
campaigns_change_status_run_and_pause_by_user_api = CampaignsUpdateMVS.as_view({
    'patch': 'campaigns_change_status_run_and_pause_by_user_api'
})
campaigns_delete_by_user_api = CampaignsUpdateMVS.as_view({
    'delete': 'campaigns_delete_by_user_api'
})
campaigns_update_by_user_api = CampaignsUpdateMVS.as_view({
    'patch': 'campaigns_update_by_user_api'
})
campaigns_add_with_draft_mode_by_user_api = CampaignsUpdateMVS.as_view({
    'post': 'campaigns_add_with_draft_mode_by_user_api'
})
campaigns_edit_with_draft_mode_by_user_api = CampaignsUpdateMVS.as_view({
    'patch': 'campaigns_edit_with_draft_mode_by_user_api'
})
campaigns_change_status_to_pause_by_user_api = CampaignsUpdateMVS.as_view({
    'patch': 'campaigns_change_status_to_pause_by_user_api'
})
campaigns_change_status_to_run_by_user_api = CampaignsUpdateMVS.as_view({
    'patch': 'campaigns_change_status_to_run_by_user_api'
})


# CampaignsPlatforms
campaigns_platforms_change_status_run_and_pause_by_user_api = CampaignsPlatformsUpdateMVS.as_view({
    'patch': 'campaigns_platforms_change_status_run_and_pause_by_user_api'
})
campaigns_platform_ungroup_get_all_by_user_api = CampaignsPlatformsUnGroupMVS.as_view({
    'get': 'campaigns_platform_ungroup_get_all_by_user_api'
})

# ===============================================

# AdSets
ad_sets_get_all_by_user_api = AdSetsMVS.as_view({
    'get': 'ad_sets_get_all_by_user_api'
})
ad_sets_get_all_by_user_1_api = AdSetsMVS.as_view({
    'get': 'ad_sets_get_all_by_user_1_api'
})
ad_sets_ungroup_get_all_by_user_api = AdSetsMVS.as_view({
    'get': 'ad_sets_ungroup_get_all_by_user_api'
})
ad_sets_get_all_by_user_and_campaign_api = AdSetsMVS.as_view({
    'get': 'ad_sets_get_all_by_user_and_campaign_api'
})
ad_sets_filter_all_by_user_and_start_end_date_api = AdSetsMVS.as_view({
    'get': 'ad_sets_filter_all_by_user_and_start_end_date_api'
})
ad_sets_change_status_run_and_pause_by_user_api = AdSetsUpdateMVS.as_view({
    'patch': 'ad_sets_change_status_run_and_pause_by_user_api'
})
ad_sets_delete_by_user_api = AdSetsUpdateMVS.as_view({
    'delete': 'ad_sets_delete_by_user_api'
})
ad_sets_update_by_user_api = AdSetsUpdateMVS.as_view({
    'patch': 'ad_sets_update_by_user_api'
})
ad_sets_add_with_campaign_by_user_api = AdSetsUpdateMVS.as_view({
    'post': 'ad_sets_add_with_campaign_by_user_api'
})
ad_sets_update_existing_by_user_api = AdSetsUpdateMVS.as_view({
    'patch': 'ad_sets_update_existing_by_user_api'
})

# AdSetsPlatforms
ad_sets_platforms_change_status_run_and_pause_by_user_api = AdSetsPlatformsUpdateMVS.as_view({
    'patch': 'ad_sets_platforms_change_status_run_and_pause_by_user_api'
})
ad_sets_platform_ungroup_get_all_by_user_api = AdSetsPlatformsUnGroupMVS.as_view({
    'get': 'ad_sets_platform_ungroup_get_all_by_user_api'
})

# ===============================================

# Ads
ads_get_all_by_user_api = AdsMVS.as_view({
    'get': 'ads_get_all_by_user_api'
})
ads_get_all_by_user_1_api = AdsMVS.as_view({
    'get': 'ads_get_all_by_user_1_api'
})
ads_get_all_by_user_and_ad_set_api = AdsMVS.as_view({
    'get': 'ads_get_all_by_user_and_ad_set_api'
})
ads_get_all_by_user_and_campaign_api = AdsMVS.as_view({
    'get': 'ads_get_all_by_user_and_campaign_api'
})
ads_filter_all_by_user_and_start_end_date_api = AdsMVS.as_view({
    'get': 'ads_filter_all_by_user_and_start_end_date_api'
})
ads_ungroup_get_all_by_user_api = AdsMVS.as_view({
    'get': 'ads_ungroup_get_all_by_user_api'
})
# 
ads_change_status_run_and_pause_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_change_status_run_and_pause_by_user_api'
})
ads_delete_by_user_api = AdsUpdateMVS.as_view({
    'delete': 'ads_delete_by_user_api'
})
ads_update_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_by_user_api'
})
# 
ads_add_common_by_user_api = AdsUpdateMVS.as_view({
    'post': 'ads_add_common_by_user_api'
})
# 
ads_add_google_only_by_user_api = AdsUpdateMVS.as_view({
    'post': 'ads_add_google_only_by_user_api'
})
ads_add_pinterest_only_by_user_api = AdsUpdateMVS.as_view({
    'post': 'ads_add_pinterest_only_by_user_api'
})
ads_add_min1080x1080_image_by_user_api = AdsUpdateMVS.as_view({
    'post': 'ads_add_min1080x1080_image_by_user_api'
})
ads_add_1296x1080_image_by_user_api = AdsUpdateMVS.as_view({
    'post': 'ads_add_1296x1080_image_by_user_api'
})
ads_add_1080x1080_image_by_user_api = AdsUpdateMVS.as_view({
    'post': 'ads_add_1080x1080_image_by_user_api'
})
ads_add_1080x1920_image_by_user_api = AdsUpdateMVS.as_view({
    'post': 'ads_add_1080x1920_image_by_user_api'
})
ads_add_Min1080x1080_video_by_user_api = AdsUpdateMVS.as_view({
    'post': 'ads_add_Min1080x1080_video_by_user_api'
})
ads_add_1080x1920_video_by_user_api = AdsUpdateMVS.as_view({
    'post': 'ads_add_1080x1920_video_by_user_api'
})
# 
ads_update_google_only_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_google_only_by_user_api'
})
ads_update_youtube_only_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_youtube_only_by_user_api'
})
ads_update_pinterest_only_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_pinterest_only_by_user_api'
})
ads_update_min1080x1080_image_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_min1080x1080_image_by_user_api'
})
ads_update_1080x1080_image_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_1080x1080_image_by_user_api'
})
ads_update_1296x1080_image_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_1296x1080_image_by_user_api'
})
ads_update_1080x1920_image_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_1080x1920_image_by_user_api'
})
ads_update_min1080x1080_video_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_min1080x1080_video_by_user_api'
})
ads_update_1080x1920_video_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_1080x1920_video_by_user_api'
})
ads_update_status_run_on_by_user_api = AdsUpdateMVS.as_view({
    'patch': 'ads_update_status_run_on_by_user_api'
})

# AdsPerformance
ads_performance_get_all_by_user_api = AdsPerformanceMVS.as_view({
    'get': 'ads_performance_get_all_by_user_api'
})
ads_performance_ungroup_get_all_by_user_api = AdsPerformanceMVS.as_view({
    'get': 'ads_performance_ungroup_get_all_by_user_api'
})
# 
ads_performance_change_status_run_and_pause_by_user_api = AdsPerformanceUpdateMVS.as_view({
    'patch': 'ads_performance_change_status_run_and_pause_by_user_api'
})
# AdsPlatforms
ads_platforms_change_status_run_and_pause_by_user_api = AdsPlatformsUpdateMVS.as_view({
    'patch': 'ads_platforms_change_status_run_and_pause_by_user_api'
})
ads_platform_ungroup_get_all_by_user_api = AdsPlatformsUnGroupMVS.as_view({
    'get': 'ads_platform_ungroup_get_all_by_user_api'
})
ads_manager_index = AdsManagerView.as_view({
    'get': 'ads_manager_index'
})

urlpatterns = [
    # Campaigns
    path('campaign_get_by_id_and_user_api/<int:campaign_id>/',
         campaign_get_by_id_and_user_api),
    path('campaigns_basic_get_all_by_user_api/',
         campaigns_basic_get_all_by_user_api),
    path('campaigns_get_all_by_user_api/<str:start_date>/<str:end_date>/',
         campaigns_get_all_by_user_api),
    path('campaigns_get_all_by_user_1_api/<str:start_date>/<str:end_date>/',
         campaigns_get_all_by_user_1_api),
    path('campaigns_filter_all_by_user_and_start_end_date_api/<str:start_date>/<str:end_date>/',
         campaigns_filter_all_by_user_and_start_end_date_api),
    path('campaigns_change_status_run_and_pause_by_user_api/',
         campaigns_change_status_run_and_pause_by_user_api),
    path('campaigns_delete_by_user_api/',
         campaigns_delete_by_user_api),
    path('campaigns_update_by_user_api/',
         campaigns_update_by_user_api),
    path('campaigns_add_with_draft_mode_by_user_api/',
         campaigns_add_with_draft_mode_by_user_api),
    path('campaigns_edit_with_draft_mode_by_user_api/',
         campaigns_edit_with_draft_mode_by_user_api),
    path('campaigns_change_status_to_pause_by_user_api/',
         campaigns_change_status_to_pause_by_user_api),
    path('campaigns_change_status_to_run_by_user_api/',
         campaigns_change_status_to_run_by_user_api),
    # 
    path('campaigns_ungroup_get_all_by_user_api/<str:start_date>/<str:end_date>/',
         campaigns_ungroup_get_all_by_user_api),    
  
    # CampaignsPlatforms
    path('campaigns_platforms_change_status_run_and_pause_by_user_api/',
         campaigns_platforms_change_status_run_and_pause_by_user_api), 
    path('campaigns_platform_ungroup_get_all_by_user_api/<str:start_date>/<str:end_date>/',
         campaigns_platform_ungroup_get_all_by_user_api),      

    # =============================================
    # AdSets
    path('ad_sets_get_all_by_user_api/<str:start_date>/<str:end_date>/',
         ad_sets_get_all_by_user_api),
    path('ad_sets_get_all_by_user_1_api/<str:start_date>/<str:end_date>/',
         ad_sets_get_all_by_user_1_api),
    path('ad_sets_get_all_by_user_and_campaign_api/<int:campaign_id>/',
         ad_sets_get_all_by_user_and_campaign_api),
    path('ad_sets_filter_all_by_user_and_start_end_date_api/<str:start_date>/<str:end_date>/',
         ad_sets_filter_all_by_user_and_start_end_date_api),
    path('ad_sets_change_status_run_and_pause_by_user_api/',
         ad_sets_change_status_run_and_pause_by_user_api),
    path('ad_sets_delete_by_user_api/',
         ad_sets_delete_by_user_api),
    path('ad_sets_update_by_user_api/',
         ad_sets_update_by_user_api),
    path('ad_sets_add_with_campaign_by_user_api/',
         ad_sets_add_with_campaign_by_user_api),
    path('ad_sets_update_existing_by_user_api/',
         ad_sets_update_existing_by_user_api),
    # 
    path('ad_sets_ungroup_get_all_by_user_api/<str:start_date>/<str:end_date>/',
         ad_sets_ungroup_get_all_by_user_api),
   
    # AdSetsPlatforms
    path('ad_sets_platforms_change_status_run_and_pause_by_user_api/',
         ad_sets_platforms_change_status_run_and_pause_by_user_api), 
    path('ad_sets_platform_ungroup_get_all_by_user_api/<str:start_date>/<str:end_date>/',
         ad_sets_platform_ungroup_get_all_by_user_api),        

    # =============================================
    # Ads
    path('ads_get_all_by_user_api/<str:start_date>/<str:end_date>/',
         ads_get_all_by_user_api),
    path('ads_get_all_by_user_1_api/<str:start_date>/<str:end_date>/',
         ads_get_all_by_user_1_api),
    path('ads_get_all_by_user_and_ad_set_api/<int:ad_set_id>/',
         ads_get_all_by_user_and_ad_set_api),
    path('ads_get_all_by_user_and_campaign_api/<int:campaign_id>/',
         ads_get_all_by_user_and_campaign_api),
    path('ads_filter_all_by_user_and_start_end_date_api/<str:start_date>/<str:end_date>/',
         ads_filter_all_by_user_and_start_end_date_api),
    # 
    path('ads_ungroup_get_all_by_user_api/<str:start_date>/<str:end_date>/',
         ads_ungroup_get_all_by_user_api),
    # 
    path('ads_change_status_run_and_pause_by_user_api/',
         ads_change_status_run_and_pause_by_user_api),
    path('ads_delete_by_user_api/',
         ads_delete_by_user_api),
    path('ads_update_by_user_api/',
         ads_update_by_user_api),
    path('ads_add_common_by_user_api/',
         ads_add_common_by_user_api),
    # 
    path('ads_add_google_only_by_user_api/',
         ads_add_google_only_by_user_api),
    path('ads_add_pinterest_only_by_user_api/',
         ads_add_pinterest_only_by_user_api),
    path('ads_add_min1080x1080_image_by_user_api/',
         ads_add_min1080x1080_image_by_user_api),
    path('ads_add_1296x1080_image_by_user_api/',
         ads_add_1296x1080_image_by_user_api),
    path('ads_add_1080x1080_image_by_user_api/',
         ads_add_1080x1080_image_by_user_api),
    path('ads_add_1080x1920_image_by_user_api/',
         ads_add_1080x1920_image_by_user_api),
    path('ads_add_Min1080x1080_video_by_user_api/',
         ads_add_Min1080x1080_video_by_user_api),
    path('ads_add_1080x1920_video_by_user_api/',
         ads_add_1080x1920_video_by_user_api),
    # 
    path('ads_update_google_only_by_user_api/',
         ads_update_google_only_by_user_api),
    path('ads_update_youtube_only_by_user_api/',
         ads_update_youtube_only_by_user_api),
    path('ads_update_pinterest_only_by_user_api/',
         ads_update_pinterest_only_by_user_api),
    path('ads_update_min1080x1080_image_by_user_api/',
         ads_update_min1080x1080_image_by_user_api),
    path('ads_update_1080x1080_image_by_user_api/',
         ads_update_1080x1080_image_by_user_api),
    path('ads_update_1296x1080_image_by_user_api/',
         ads_update_1296x1080_image_by_user_api),
    path('ads_update_1080x1920_image_by_user_api/',
         ads_update_1080x1920_image_by_user_api),
    path('ads_update_min1080x1080_video_by_user_api/',
         ads_update_min1080x1080_video_by_user_api),
    path('ads_update_1080x1920_video_by_user_api/',
         ads_update_1080x1920_video_by_user_api),
    path('ads_update_status_run_on_by_user_api/',
         ads_update_status_run_on_by_user_api),

    # AdsPerformance
    path('ads_performance_get_all_by_user_api/',
         ads_performance_get_all_by_user_api),
    path('ads_performance_ungroup_get_all_by_user_api/<str:start_date>/<str:end_date>/',
         ads_performance_ungroup_get_all_by_user_api),
    # 
    path('ads_performance_change_status_run_and_pause_by_user_api/',
         ads_performance_change_status_run_and_pause_by_user_api),

    # AdsPlatforms
    path('ads_platforms_change_status_run_and_pause_by_user_api/',
         ads_platforms_change_status_run_and_pause_by_user_api), 
    path('ads_platform_ungroup_get_all_by_user_api/<str:start_date>/<str:end_date>/',
         ads_platform_ungroup_get_all_by_user_api),        

    path('ads_manager_index/<str:start_date>/<str:end_date>/',
         ads_manager_index),
    path('notif/', ad_manager_notif, name='ad-manager-notif'),
]