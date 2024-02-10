from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from django.forms.models import model_to_dict
import re
from rest_framework.parsers import MultiPartParser, FormParser
import jwt

from api.media_library.models import *
from .serializers import *
from api.authentication.serializers.login import _get_user_id_from_token
# from api import status_http

class MediaMVS(viewsets.ModelViewSet):
    serializer_class = MediaSerializer
    serializer_class_1 = MediaDeleteSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=["GET"], detail=False, url_path="get_all_image_by_user_api", url_name="get_all_image_by_user_api")
    def get_all_image_by_user_api(self, request, *args, **kwargs):
        user_id = _get_user_id_from_token(request)    
        search_value =  request.query_params.get('search_value')
        words = re.split(r"[-;,.\s]\s*", search_value)
        query = Q()
        for word in words:
            word = word.lower()
            query |= Q(display_file_name__icontains=word)
        query &= Q(user_id=user_id)
        # 
        sort_by = request.query_params.get('sort_by').strip()
        # print("sort_by=", sort_by)
        list_order_by = ('-id')  
        if len(sort_by) > 0:
            if sort_by=='name':
                list_order_by = ('-display_file_name')  
            if sort_by=='size':
                list_order_by = ('-size')  
            if sort_by=='date':
                list_order_by = ('-uploaded')  
            if sort_by=='imp':
                list_order_by = ('-impressions')  
            if sort_by=='clicks':
                list_order_by = ('-clicks')  
            if sort_by=='spent':
                list_order_by = ('-spent')
        if len(search_value) == 0:
            queryset = Media.objects.filter(user_id=user_id).order_by(list_order_by)
        else:
            queryset = Media.objects.filter(query).order_by(list_order_by)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["DELETE"], detail=False, url_path="delete_image_by_user_api", url_name="delete_image_by_user_api")
    def delete_image_by_user_api(self, request, *args, **kwargs):
        try:
            user_id = _get_user_id_from_token(request)  
            context = {'user_id': user_id}
            serializer = self.serializer_class_1(data=request.data, context=context)
            if serializer.is_valid():
                data = {}
                result = serializer.delete(request)
                if result:
                    data['message'] = 'Delete successfully!'
                    return Response(data, status=status.HTTP_204_NO_CONTENT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print(
                "MediaMVS_delete_image_by_user_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)   

class UploadImageLibraryMVS(viewsets.ModelViewSet):
    serializer_class = UploadImageLibrarySerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @action(methods=["POST"], detail=False, url_path="upload_image_api", url_name="upload_image_api")
    def upload_image_api(self, request, *args, **kwargs):
        try:
            user_id = _get_user_id_from_token(request)    
            context = {'user_id': user_id}
            # print("upload_image_api: ", request.data)
            serializer = self.serializer_class(data=request.data, context=context)
            if serializer.is_valid():
                serializer.upload(request)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("upload_image_api: ", error)
        return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)