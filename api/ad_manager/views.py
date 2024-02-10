from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.decorators import action
from django.db.models import Q, Value, CharField, F
import re

import sys
import os

from .models import *
from .serializers import *
from api.authentication.serializers.login import _get_user_id_from_token
from .status_http import *

from api.meta.utils.create_campaign import create_campaign

from rest_framework_tracking.mixins import LoggingMixin

from core.utils.checkStatus import checkStatus

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from rest_framework.decorators import api_view

# Common ===============================================
# /////////////
# Common End ===========================================

# Campaign =============================================

class CampaignsPagination(LoggingMixin, PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_paginated_response(self, data):
        next_page = previous_page = None
        if self.page.has_next():
            next_page = self.page.next_page_number()
        if self.page.has_previous():
            previous_page = self.page.previous_page_number()
        return Response({
            'totalRows': self.page.paginator.count,
            'page_size': self.page_size,
            'current_page': self.page.number,
            'next_page': next_page,
            'previous_page': previous_page,
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'data': data,
        })

class CampaignsMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = CampaignsSerializer
    serializer_class_basic = CampaignsBasicSerializer
    permission_classes = [IsAuthenticated,]
    pagination_class = CampaignsPagination

    @action(methods=["GET"], detail=False, url_path="campaigns_basic_get_all_by_user_api", url_name="campaigns_basic_get_all_by_user_api")
    def campaigns_basic_get_all_by_user_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        # user_id = 2
        queryset = Campaigns.objects.filter(user_id=user_id, is_deleted=False).order_by('-created')  
        serializer = self.serializer_class_basic(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="campaigns_get_all_by_user_api", url_name="campaigns_get_all_by_user_api")
    def campaigns_get_all_by_user_api(self, request, *args, **kwargs):        
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        if start_date != "null" and end_date != "null":
            query &= Q(user_id=user_id, is_deleted=False, campaigns_performance__date__gte=start_date, campaigns_performance__date__lte=end_date)
            queryset = Campaigns.objects.filter(query).distinct().order_by('-created')    
        else:
            query &= Q(user_id=user_id, is_deleted=False)
            queryset = Campaigns.objects.filter(query).order_by('-created') 
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True, context={'start_date': start_date, 'end_date': end_date})
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="campaigns_get_all_by_user_1_api", url_name="campaigns_get_all_by_user_1_api")
    def campaigns_get_all_by_user_1_api(self, request, *args, **kwargs):
        # total_spend_campaign = CampaignsPerformance.objects.filter(campaign_id=7).aggregate(Sum('spend'))['spend__sum']
        # print("total_spend_campaign: ", total_spend_campaign)
        user_id = _get_user_id_from_token(request) 
        # user_id = 2
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        query &= Q(user_id=user_id, is_deleted=False)
        queryset = Campaigns.objects.filter(query).order_by('-created') 
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(methods=["GET"], detail=False, url_path="campaigns_ungroup_get_all_by_user_api", url_name="campaigns_ungroup_get_all_by_user_api")
    def campaigns_ungroup_get_all_by_user_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        if start_date != "null" and end_date != "null":
            query &= Q(user_id=user_id, is_deleted=False, campaigns_performance__date__gte=start_date, campaigns_performance__date__lte=end_date)
            queryset = Campaigns.objects.filter(query).distinct().order_by('-created')    
        else:
            query &= Q(user_id=user_id, is_deleted=False)
            queryset = Campaigns.objects.filter(query).order_by('-created') 
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True, context={'start_date': start_date, 'end_date': end_date})
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(methods=["GET"], detail=False, url_path="campaigns_filter_all_by_user_and_start_end_date_api", url_name="campaigns_filter_all_by_user_and_start_end_date_api")
    def campaigns_filter_all_by_user_and_start_end_date_api(self, request, *args, **kwargs):
        # user_id = _get_user_id_from_token(request) 
        user_id = 2
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        queryset = Campaigns.objects.filter(user_id=user_id, is_deleted=False, start_date__gte=start_date, end_date__lte=end_date).order_by('-created')    
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="campaign_get_by_id_and_user_api", url_name="campaign_get_by_id_and_user_api")
    def campaign_get_by_id_and_user_api(self, request, *args, **kwargs):
        try:
            user_id = _get_user_id_from_token(request) 
            # user_id = 2
            campaign_id = kwargs['campaign_id']
            if campaign_id == 0:
                return Response({}, status=status.HTTP_200_OK)
            queryset = Campaigns.objects.get(pk=campaign_id, user_id=user_id)
            serializer = self.serializer_class(queryset, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as err:
            print("CampaignsMVS_campaign_get_by_id_and_user_api: ", err)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

class CampaignsUpdateMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = CampaignsUpdateSerializer
    permission_classes = [IsAuthenticated,]

    @action(methods=["PATCH"], detail=False, url_path="campaigns_change_status_run_and_pause_by_user_api", url_name="campaigns_change_status_run_and_pause_by_user_api")
    def campaigns_change_status_run_and_pause_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                result = serializer.changeStatusRunPause(request)
                return Response(result, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("CampaignsUpdateMVS_campaigns_change_status_run_and_pause_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["DELETE"], detail=False, url_path="campaigns_delete_by_user_api", url_name="campaigns_delete_by_user_api")
    def campaigns_delete_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.delete(request)                
                data = {}
                data['message'] = 'Delete successfully!'
                return Response(data, status=status.HTTP_204_NO_CONTENT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("CampaignsUpdateMVS_campaigns_delete_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="campaigns_update_by_user_api", url_name="campaigns_update_by_user_api")
    def campaigns_update_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():  
                # if not serializer.name_validate_update(request):
                #     return Response(serializer.errors, status=HTTP_ME_458_DUPLICATE)               
                result = serializer.update(request)
                # data['message'] = 'Update successfully!'
                return Response(result, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("CampaignsUpdateMVS_campaigns_update_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="campaigns_add_with_draft_mode_by_user_api", url_name="campaigns_add_with_draft_mode_by_user_api")
    def campaigns_add_with_draft_mode_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid(): 
                # if not serializer.name_validate_add(request):
                #     return Response(serializer.errors, status=HTTP_ME_458_DUPLICATE)               
                result = serializer.add_with_draft_mode(request)
                # print("result: ", result)
               
                result['message'] = 'Add with draft mode successfully!'
                return Response(result, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("CampaignsUpdateMVS_add_with_draft_mode_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="campaigns_edit_with_draft_mode_by_user_api", url_name="campaigns_edit_with_draft_mode_by_user_api")
    def campaigns_edit_with_draft_mode_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid(): 
                # if not serializer.name_validate_add(request):
                #     return Response(serializer.errors, status=HTTP_ME_458_DUPLICATE)               
                result = serializer.edit_with_draft_mode(request)
                # print("result: ", result)                
                result['message'] = 'Edit with draft mode successfully!'
                return Response(result, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("CampaignsUpdateMVS_edit_with_draft_mode_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=["PATCH"], detail=False, url_path="campaigns_change_status_to_pause_by_user_api", url_name="campaigns_change_status_to_pause_by_user_api")
    def campaigns_change_status_to_pause_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.changeStatusToPause(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("CampaignsUpdateMVS_campaigns_change_status_to_pause_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="campaigns_change_status_to_run_by_user_api", url_name="campaigns_change_status_to_run_by_user_api")
    def campaigns_change_status_to_run_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.changeStatusToRun(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("CampaignsUpdateMVS_campaigns_change_status_to_run_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)


class CampaignsPlatformsUpdateMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = CampaignsPlatformsUpdateSerializer
    permission_classes = [IsAuthenticated,]

    @action(methods=["PATCH"], detail=False, url_path="campaigns_platforms_change_status_run_and_pause_by_user_api", url_name="campaigns_platforms_change_status_run_and_pause_by_user_api")
    def campaigns_platforms_change_status_run_and_pause_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.changeStatusRunPause(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("CampaignsPlatformsUpdateMVS_campaigns_platforms_change_status_run_and_pause_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)
    
class CampaignsPlatformsUnGroupMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = CampaignsPlatformsUnGroupSerializer
    permission_classes = [IsAuthenticated,]      
    
    @action(methods=["GET"], detail=False, url_path="campaigns_platform_ungroup_get_all_by_user_api", url_name="campaigns_platform_ungroup_get_all_by_user_api")
    def campaigns_platform_ungroup_get_all_by_user_api(self, request, *args, **kwargs):
        try:
            user_id = _get_user_id_from_token(request) 
            query = Q()
            start_date = kwargs['start_date']
            end_date = kwargs['end_date']
            query &= Q(campaign__user_id=user_id, campaign__is_deleted=False)
            queryset = CampaignsPlatforms.objects.filter(query)
            serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print("this is error",e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
            error_message = 'ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno
            print(error_message)
            return Response({
                'status' : 'Error',
                'message': 'There was an error',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# class CampaignsPlatformsMVS(viewsets.ModelViewSet):
#     serializer_class = CampaignsPlatformsSerializer
#     permission_classes = [IsAuthenticated,]
#     pagination_class = CampaignsPagination
#     # serializer_class_ungroup = CampaignsPlatformsUnGroupSerializer

#     @action(methods=["GET"], detail=False, url_path="campaigns_platforms_get_all_by_user_api", url_name="campaigns_platforms_get_all_by_user_api")
#     def campaigns_platforms_get_all_by_user_api(self, request, *args, **kwargs):
#         user_id = _get_user_id_from_token(request) 
#         # user_id = 2
#         queryset = CampaignsPlatforms.objects.filter(campaign__user_id=user_id).order_by('date')  
#         # page = self.paginate_queryset(queryset)
#         # if page is not None:
#         #     serializer = self.get_serializer(page, many=True)
#         #     return self.get_paginated_response(serializer.data) 
#         serializer = self.serializer_class(queryset, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
    
#     @action(methods=["GET"], detail=False, url_path="campaigns_platforms_ungroup_get_all_by_user_api", url_name="campaigns_platforms_ungroup_get_all_by_user_api")
#     def campaigns_platforms_ungroup_get_all_by_user_api(self, request, *args, **kwargs):
#         user_id = _get_user_id_from_token(request) 
#         # user_id = 2
#         search_value = request.GET["search_value"]
#         words = re.split(r"[-;,.\s]\s*", search_value)
#         query = Q()
#         for word in words:
#             query |= Q(campaign__name__icontains=word)        
#         # print("campaigns_platforms_ungroup_get_all_by_user_api: ", search_value)
#         start_date = kwargs['start_date']
#         end_date = kwargs['end_date']
#         if start_date != "null" and end_date != "null":
#             query &= Q(campaign__is_deleted=False, campaign__user_id=user_id, date__gte=start_date, date__lte=end_date)
#             queryset = CampaignsPlatforms.objects.values("publisher_platform", "ad_platform") \
#                 .annotate(id=Min('id'), campaign_id=F("campaign__id"), campaign_name=F("campaign__name"), impressions=Sum('impressions'), clicks=Sum('clicks'), actions=Sum('actions'),spend=Sum('spend'),earned=Sum('earned'),) \
#                 .filter(query) 
#         else:
#             query &= Q(campaign__is_deleted=False, campaign__user_id=user_id)
#             queryset = CampaignsPlatforms.objects.values("publisher_platform", "ad_platform") \
#                 .annotate(id=Min('id'), campaign_id=F("campaign__id"), campaign_name=F("campaign__name"), impressions=Sum('impressions'), clicks=Sum('clicks'), actions=Sum('actions'),spend=Sum('spend'),earned=Sum('earned'),) \
#                 .filter(query)
#         serializer = self.serializer_class_ungroup(queryset, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
    
# Campaign End =========================================

# AdSet =============================================

class AdSetsPagination(LoggingMixin, PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_paginated_response(self, data):
        next_page = previous_page = None
        if self.page.has_next():
            next_page = self.page.next_page_number()
        if self.page.has_previous():
            previous_page = self.page.previous_page_number()
        return Response({
            'totalRows': self.page.paginator.count,
            'page_size': self.page_size,
            'current_page': self.page.number,
            'next_page': next_page,
            'previous_page': previous_page,
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'data': data,
        })

class AdSetsMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = AdSetsSerializer
    permission_classes = [IsAuthenticated,]
    pagination_class = AdSetsPagination

    @action(methods=["GET"], detail=False, url_path="ad_sets_get_all_by_user_api", url_name="ad_sets_get_all_by_user_api")
    def ad_sets_get_all_by_user_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        if start_date != "null" and end_date != "null":
            query &= Q(user_id=user_id, is_deleted=False, ad_sets_performance__date__gte=start_date, ad_sets_performance__date__lte=end_date)
            queryset = AdSets.objects.filter(query).distinct().order_by('created')
        else:
            query &= Q(user_id=user_id, is_deleted=False)
            queryset = AdSets.objects.filter(query).order_by('created')
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True, context={'start_date': start_date, 'end_date': end_date})
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="ad_sets_get_all_by_user_api", url_name="ad_sets_get_all_by_user_api")
    def ad_sets_get_all_by_user_1_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        query &= Q(user_id=user_id, is_deleted=False)
        queryset = AdSets.objects.filter(query).order_by('created')   
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(methods=["GET"], detail=False, url_path="ad_sets_ungroup_get_all_by_user_api", url_name="ad_sets_ungroup_get_all_by_user_api")
    def ad_sets_ungroup_get_all_by_user_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        if start_date != "null" and end_date != "null":
            query &= Q(user_id=user_id, is_deleted=False, ad_sets_performance__date__gte=start_date, ad_sets_performance__date__lte=end_date)
            queryset = AdSets.objects.filter(query).distinct().order_by('created')
        else:
            query &= Q(user_id=user_id, is_deleted=False)
            queryset = AdSets.objects.filter(query).order_by('created')
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True, context={'start_date': start_date, 'end_date': end_date})
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(methods=["GET"], detail=False, url_path="ad_sets_get_all_by_user_and_campaign_api", url_name="ad_sets_get_all_by_user_and_campaign_api")
    def ad_sets_get_all_by_user_and_campaign_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        # user_id = 2
        campaign_id = kwargs['campaign_id']
        queryset = AdSets.objects.filter(user_id=user_id, is_deleted=False, campaign__id=campaign_id).order_by('created')    
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="ad_sets_filter_all_by_user_and_start_end_date_api", url_name="ad_sets_filter_all_by_user_and_start_end_date_api")
    def ad_sets_filter_all_by_user_and_start_end_date_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        # user_id = 2
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        queryset = AdSets.objects.filter(user_id=user_id, is_deleted=False, campaign__start_date__gte=start_date, campaign__end_date__lte=end_date).order_by('created')    
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AdSetsUpdateMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = AdSetsUpdateSerializer
    permission_classes = [IsAuthenticated,]

    @action(methods=["PATCH"], detail=False, url_path="ad_sets_change_status_run_and_pause_by_user_api", url_name="ad_sets_change_status_run_and_pause_by_user_api")
    def ad_sets_change_status_run_and_pause_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                data = serializer.changeStatusRunPause(request)
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdSetsUpdateMVS_ad_sets_change_status_run_and_pause_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["DELETE"], detail=False, url_path="ad_sets_delete_by_user_api", url_name="ad_sets_delete_by_user_api")
    def ad_sets_delete_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.delete(request)                
                data = {}
                data['message'] = 'Delete successfully!'
                return Response(data, status=status.HTTP_204_NO_CONTENT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdSetsUpdateMVS_ad_sets_delete_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="ad_sets_update_by_user_api", url_name="ad_sets_update_by_user_api")
    def ad_sets_update_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                result = serializer.update(request)
                result['message'] = 'Update successfully!'
                return Response(result, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdSetsUpdateMVS_ad_sets_update_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="ad_sets_add_with_campaign_by_user_api", url_name="ad_sets_add_with_campaign_by_user_api")
    def ad_sets_add_with_campaign_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                result = serializer.add_from_campaign(request)                
                result['message'] = 'Add with campaign successfully!'
                return Response(result, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("CampaignsUpdateMVS_ad_sets_add_with_campaign_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="ad_sets_update_existing_by_user_api", url_name="ad_sets_update_existing_by_user_api")
    def ad_sets_update_existing_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                result = serializer.updateExisting(request)                
                result['message'] = 'Update successfully!'
                return Response(result, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdSetsUpdateMVS_ad_sets_update_existing_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

class AdSetsPlatformsUpdateMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = AdSetsPlatformsUpdateSerializer
    permission_classes = [IsAuthenticated,]

    @action(methods=["PATCH"], detail=False, url_path="ad_sets_platforms_change_status_run_and_pause_by_user_api", url_name="ad_sets_platforms_change_status_run_and_pause_by_user_api")
    def ad_sets_platforms_change_status_run_and_pause_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                data = serializer.changeStatusRunPause(request)
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdSetsPlatformsUpdateMVS_ad_sets_platforms_change_status_run_and_pause_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)
    
class AdSetsPlatformsUnGroupMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = AdSetsPlatformsUnGroupSerializer
    permission_classes = [IsAuthenticated,]      
    
    @action(methods=["GET"], detail=False, url_path="ad_sets_platform_ungroup_get_all_by_user_api", url_name="ad_sets_platform_ungroup_get_all_by_user_api")
    def ad_sets_platform_ungroup_get_all_by_user_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        query &= Q(ad_set__user_id=user_id, ad_set__is_deleted=False)
        queryset = AdSetsPlatforms.objects.filter(query)
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
# AdSet End =============================================

# Ads =============================================

class AdsPagination(LoggingMixin, PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_paginated_response(self, data):
        next_page = previous_page = None
        if self.page.has_next():
            next_page = self.page.next_page_number()
        if self.page.has_previous():
            previous_page = self.page.previous_page_number()
        return Response({
            'totalRows': self.page.paginator.count,
            'page_size': self.page_size,
            'current_page': self.page.number,
            'next_page': next_page,
            'previous_page': previous_page,
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'data': data,
        })

class AdsMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = AdsSerializer
    permission_classes = [IsAuthenticated,]
    pagination_class = AdsPagination

    @action(methods=["GET"], detail=False, url_path="ads_get_all_by_user_api", url_name="ads_get_all_by_user_api")
    def ads_get_all_by_user_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        if start_date != "null" and end_date != "null":
            query &= Q(user_id=user_id, is_deleted=False, ads_performance__date__gte=start_date, ads_performance__date__lte=end_date)
            queryset = Ads.objects.filter(query).distinct().order_by('created')
        else:
            query &= Q(user_id=user_id, is_deleted=False)
            queryset = Ads.objects.filter(query).order_by('created')
        # queryset = Ads.objects.filter(user_id=user_id, is_deleted=False).order_by('created')    
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True, context={'start_date': start_date, 'end_date': end_date})
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="ads_get_all_by_user_1_api", url_name="ads_get_all_by_user_1_api")
    def ads_get_all_by_user_1_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        query &= Q(user_id=user_id, is_deleted=False)
        queryset = Ads.objects.filter(query).order_by('created')
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(methods=["GET"], detail=False, url_path="ads_ungroup_get_all_by_user_api", url_name="ads_ungroup_get_all_by_user_api")
    def ads_ungroup_get_all_by_user_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        if start_date != "null" and end_date != "null":
            query &= Q(user_id=user_id, is_deleted=False, ads_performance__date__gte=start_date, ads_performance__date__lte=end_date)
            queryset = Ads.objects.filter(query).distinct().order_by('created')
        else:
            query &= Q(user_id=user_id, is_deleted=False)
            queryset = Ads.objects.filter(query).order_by('created')
        # queryset = Ads.objects.filter(user_id=user_id, is_deleted=False).order_by('created')    
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True, context={'start_date': start_date, 'end_date': end_date})
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(methods=["GET"], detail=False, url_path="ads_get_all_by_user_and_ad_set_api", url_name="ads_get_all_by_user_and_ad_set_api")
    def ads_get_all_by_user_and_ad_set_api(self, request, *args, **kwargs):
        # user_id = _get_user_id_from_token(request) 
        user_id = 2
        ad_set_id = kwargs['ad_set_id']
        queryset = Ads.objects.filter(user_id=user_id, is_deleted=False, ad_set__id=ad_set_id).order_by('created')    
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="ads_get_all_by_user_and_campaign_api", url_name="ads_get_all_by_user_and_campaign_api")
    def ads_get_all_by_user_and_campaign_api(self, request, *args, **kwargs):
        # user_id = _get_user_id_from_token(request) 
        user_id = 2
        campaign_id = kwargs['campaign_id']
        queryset = Ads.objects.filter(user_id=user_id, is_deleted=False, campaign__id=campaign_id).order_by('created')    
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="ads_filter_all_by_user_and_start_end_date_api", url_name="ads_filter_all_by_user_and_start_end_date_api")
    def ads_filter_all_by_user_and_start_end_date_api(self, request, *args, **kwargs):
        # user_id = _get_user_id_from_token(request) 
        user_id = 2
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        queryset = Ads.objects.filter(user_id=user_id, is_deleted=False, campaign__start_date__gte=start_date, campaign__end_date__lte=end_date).order_by('created')    
        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AdsUpdateMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = AdsUpdateSerializer
    permission_classes = [IsAuthenticated,]

    @action(methods=["PATCH"], detail=False, url_path="ads_change_status_run_and_pause_by_user_api", url_name="ads_change_status_run_and_pause_by_user_api")
    def ads_change_status_run_and_pause_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                data = serializer.changeStatusRunPause(request)                
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_change_status_run_and_pause_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["DELETE"], detail=False, url_path="ads_delete_by_user_api", url_name="ads_delete_by_user_api")
    def ads_delete_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.delete(request)                
                data = {}
                data['message'] = 'Delete successfully!'
                return Response(data, status=status.HTTP_204_NO_CONTENT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_delete_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="ads_update_by_user_api", url_name="ads_update_by_user_api")
    def ads_update_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                result = serializer.update(request)
                result['message'] = 'Update successfully!'
                return Response(result, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="ads_add_common_by_user_api", url_name="ads_add_common_by_user_api")
    def ads_add_common_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                result = serializer.add_common(request)
                print("result: ", result)
                result['message'] = 'Update successfully!'
                return Response(result, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_add_common_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)
    # ========================================================

    @action(methods=["POST"], detail=False, url_path="ads_add_google_only_by_user_api", url_name="ads_add_google_only_by_user_api")
    def ads_add_google_only_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.add_google_only(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_add_google_only_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="ads_add_pinterest_only_by_user_api", url_name="ads_add_pinterest_only_by_user_api")
    def ads_add_pinterest_only_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.add_pinterest_only(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_add_pinterest_only_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="ads_add_min1080x1080_image_by_user_api", url_name="ads_add_min1080x1080_image_by_user_api")
    def ads_add_min1080x1080_image_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.add_min1080x1080_image(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_add_min1080x1080_image_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="ads_add_1296x1080_image_by_user_api", url_name="ads_add_1296x1080_image_by_user_api")
    def ads_add_1296x1080_image_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.add_1296x1080_image(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_add_1296x1080_image_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="ads_add_1080x1080_image_by_user_api", url_name="ads_add_1080x1080_image_by_user_api")
    def ads_add_1080x1080_image_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.add_1080x1080_image(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_add_1080x1080_image_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="ads_add_1080x1920_image_by_user_api", url_name="ads_add_1080x1920_image_by_user_api")
    def ads_add_1080x1920_image_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.add_1080x1920_image(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_add_1080x1920_image_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="ads_add_Min1080x1080_video_by_user_api", url_name="ads_add_Min1080x1080_video_by_user_api")
    def ads_add_Min1080x1080_video_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.add_Min1080x1080_video(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_add_Min1080x1080_video_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="ads_add_1080x1920_video_by_user_api", url_name="ads_add_1080x1920_video_by_user_api")
    def ads_add_1080x1920_video_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.add_1080x1920_video(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_add_1080x1920_video_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    # Update

    @action(methods=["PATCH"], detail=False, url_path="ads_update_google_only_by_user_api", url_name="ads_update_google_only_by_user_api")
    def ads_update_google_only_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.update_google_only(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_google_only_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="ads_update_youtube_only_by_user_api", url_name="ads_update_youtube_only_by_user_api")
    def ads_update_youtube_only_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.update_youtube_only(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_youtube_only_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)


    @action(methods=["PATCH"], detail=False, url_path="ads_update_pinterest_only_by_user_api", url_name="ads_update_pinterest_only_by_user_api")
    def ads_update_pinterest_only_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.update_pinterest_only(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_pinterest_only_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="ads_update_min1080x1080_image_by_user_api", url_name="ads_update_min1080x1080_image_by_user_api")
    def ads_update_min1080x1080_image_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.update_min1080x1080_image(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_min1080x1080_image_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=["PATCH"], detail=False, url_path="ads_update_1080x1080_image_by_user_api", url_name="ads_update_1080x1080_image_by_user_api")
    def ads_update_1080x1080_image_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.update_1080x1080_image(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_1080x1080_image_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="ads_update_1296x1080_image_by_user_api", url_name="ads_update_1296x1080_image_by_user_api")
    def ads_update_1296x1080_image_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.update_1296x1080_image(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_1296x1080_image_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="ads_update_1080x1920_image_by_user_api", url_name="ads_update_1080x1920_image_by_user_api")
    def ads_update_1080x1920_image_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.update_1080x1920_image(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_1080x1920_image_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="ads_update_min1080x1080_video_by_user_api", url_name="ads_update_min1080x1080_video_by_user_api")
    def ads_update_min1080x1080_video_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.update_min1080x1080_video(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_min1080x1080_video_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="ads_update_1080x1920_video_by_user_api", url_name="ads_update_1080x1920_video_by_user_api")
    def ads_update_1080x1920_video_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.update_1080x1920_video(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_1080x1920_video_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="ads_update_status_run_on_by_user_api", url_name="ads_update_status_run_on_by_user_api")
    def ads_update_status_run_on_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.update_status_run_on(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsUpdateMVS_ads_update_status_run_on_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)


class AdsPerformanceMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = AdsPerformanceSerializer
    permission_classes = [IsAuthenticated,]
    pagination_class = AdsPagination
    serializer_class_ungroup = AdsPerformanceUnGroupSerializer

    @action(methods=["GET"], detail=False, url_path="ads_performance_get_all_by_user_api", url_name="ads_performance_get_all_by_user_api")
    def ads_performance_get_all_by_user_api(self, request, *args, **kwargs):
        # user_id = _get_user_id_from_token(request) 
        user_id = 2
        queryset = AdsPerformance.objects.filter(ad__user_id=user_id).order_by('date')  
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data) 
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="ads_performance_ungroup_get_all_by_user_api", url_name="ads_performance_ungroup_get_all_by_user_api")
    def ads_performance_ungroup_get_all_by_user_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        if start_date != "null" and end_date != "null":
            query &= Q(ad__is_deleted=False, ad__user_id=user_id, date__gte=start_date, date__lte=end_date)
            queryset = AdsPerformance.objects.values("publisher_platform", "ad_platform") \
                .annotate(id=Min('id'), ad_id=F("ad__id"), ad_name=F("ad__name"), impressions=Sum('impressions'), clicks=Sum('clicks'), actions=Sum('actions'),spend=Sum('spend'),earned=Sum('earned'),) \
                .filter(query) 
        else:
            query &= Q(ad__is_deleted=False, ad__user_id=user_id)
            queryset = AdsPerformance.objects.values("publisher_platform", "ad_platform") \
                .annotate(id=Min('id'), ad_id=F("ad__id"), ad_name=F("ad__name"), impressions=Sum('impressions'), clicks=Sum('clicks'), actions=Sum('actions'),spend=Sum('spend'),earned=Sum('earned'),) \
                .filter(query)
        serializer = self.serializer_class_ungroup(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class AdsPerformanceUpdateMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = AdsPerformanceUpdateSerializer
    permission_classes = [IsAuthenticated,]

    @action(methods=["PATCH"], detail=False, url_path="ads_performance_change_status_run_and_pause_by_user_api", url_name="ads_performance_change_status_run_and_pause_by_user_api")
    def ads_performance_change_status_run_and_pause_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                result = serializer.changeStatusRunPause(request)
                return Response(result, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsPerformanceUpdateMVS_ads_performance_change_status_run_and_pause_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

class AdsPlatformsUpdateMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = AdsPlatformsUpdateSerializer
    permission_classes = [IsAuthenticated,]

    @action(methods=["PATCH"], detail=False, url_path="ads_platforms_change_status_run_and_pause_by_user_api", url_name="ads_platforms_change_status_run_and_pause_by_user_api")
    def ads_platforms_change_status_run_and_pause_by_user_api(self, request, *args, **kwargs):
        try:            
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():                
                serializer.changeStatusRunPause(request)                
                data = {}
                data['message'] = 'Update successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("AdsPlatformsUpdateMVS_ads_platforms_change_status_run_and_pause_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)
    
class AdsPlatformsUnGroupMVS(LoggingMixin, viewsets.ModelViewSet):
    serializer_class = AdsPlatformsUnGroupSerializer
    permission_classes = [IsAuthenticated,]      
    
    @action(methods=["GET"], detail=False, url_path="ads_platform_ungroup_get_all_by_user_api", url_name="ads_platform_ungroup_get_all_by_user_api")
    def ads_platform_ungroup_get_all_by_user_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        query = Q()
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']
        query &= Q(ad__user_id=user_id, ad__is_deleted=False)
        queryset = AdsPlatforms.objects.filter(query)
        serializer = self.serializer_class(queryset, many=True, context={'start_date': start_date, 'end_date': end_date})
        return Response(serializer.data, status=status.HTTP_200_OK)
   
# Ads End =============================================

class AdsManagerView(LoggingMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated,]      
   
    @action(methods=["GET"], detail=False, url_path="ads_manager_index", url_name="ads_manager_index")
    def ads_manager_index(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request) 
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']

        # querysets
        campaigns_queryset = Campaigns.objects.filter(user_id=user_id, is_deleted=False)
        ad_sets_queryset = AdSets.objects.filter(user_id=user_id, is_deleted=False)
        ads_queryset = Ads.objects.filter(user_id=user_id, is_deleted=False)
        campaigns_platforms_queryset = CampaignsPlatforms.objects.filter(campaign__user_id=user_id, campaign__is_deleted=False)
        ad_sets_platforms_queryset = AdSetsPlatforms.objects.filter(ad_set__user_id=user_id, ad_set__is_deleted=False)
        ads_platforms_queryset = AdsPlatforms.objects.filter(ad__user_id=user_id, ad__is_deleted=False)
        ads_performance_queryset  = AdsPerformance.objects.values("publisher_platform", "ad_platform", "ad_id") \
                                    .annotate(id=Min('id'), impressions=Sum('impressions'), clicks=Sum('clicks'), actions=Sum('actions'),spend=Sum('spend'),earned=Sum('earned'),) \
                                    .filter(date__gte=start_date, date__lte=end_date)

        # serializers
        campaigns_serializer = CampaignsBasicUnGroupSerializer(campaigns_queryset, many=True)
        ad_sets_serializer = AdSetsTempSerializer(ad_sets_queryset, many=True)
        ads_serializer = AdsTempSerializer(ads_queryset, many=True)
        campaigns_platforms_serializer = CampaignsPlatformsTempSerializer(campaigns_platforms_queryset, many=True)
        ad_sets_platforms_serializer = AdsetsPlatformsTempSerializer(ad_sets_platforms_queryset, many=True)
        ads_platforms_serializer = AdsPlatformsTempSerializer(ads_platforms_queryset, many=True)
        ads_performance_serializer = AdsPerformanceTempSerializer(ads_performance_queryset, many=True)

        for c in campaigns_queryset:
            if c.status != 'PAUSED':
                total_spend = AdsPerformance.objects.filter(ad__campaign_id=c.id).aggregate(Sum('spend'))['spend__sum']
                total_spend_today = AdsPerformance.objects.filter(ad__campaign_id=c.id, date=timezone.now().date()).aggregate(Sum('spend'))['spend__sum']
                c.status = checkStatus(**{'start_date': c.start_date, 'end_date': c.end_date, 'total_spend': total_spend, 'total_spend_today': total_spend_today, 'budget': c.budget, 'daily_budget': c.daily_budget})
                c.save()

                c.campaigns_platform.exclude(status='PAUSED').update(status=c.status)

        return Response({
            'campaigns': campaigns_serializer.data,
            'ad_sets': ad_sets_serializer.data,
            'ads': ads_serializer.data,
            'campaigns_platforms': campaigns_platforms_serializer.data,
            'ad_sets_platforms': ad_sets_platforms_serializer.data,
            'ads_platforms': ads_platforms_serializer.data,
            'ads_performance': ads_performance_serializer.data,
        })
        

@api_view(['POST'])
def ad_manager_notif(request):
    if request.data.get('message'):
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)('ad-manager', {
            'type': 'send_notification',
            'message': request.data.get('message'),
        })

    return Response(status=200)