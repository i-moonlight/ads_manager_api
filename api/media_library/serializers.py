from rest_framework import serializers
# from django.contrib.auth.models import User
# from django.db.models import Q
# from django.utils.text import slugify
from api.media_library.models import *
import boto3
from django.conf import settings
import cv2
from PIL import Image
from io import BytesIO
import os
import sys


def get_s3_bucket_path(bucket_name):
    # Create an S3 client
    s3 = boto3.client('s3')

    # Get the region of the S3 bucket
    location = s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint']

    # Generate the URL for the S3 bucket
    if location:
        url = f"https://{bucket_name}.s3.{location}.amazonaws.com/"
    else:
        url = f"https://{bucket_name}.s3.amazonaws.com/"

    return url

class UploadImageLibrarySerializer(serializers.ModelSerializer):
    files = serializers.ListField(child = serializers.FileField(required=True))
    infoFiles = serializers.ListField(child=serializers.CharField(required=False))
    file_type = serializers.CharField(required=False)
    display_file_name = serializers.CharField(required=False)
    user = serializers.CharField(required=False)
    
    class Meta:
        model = Media
        fields = '__all__'
        extra_fields =  [
            'files', 'infoFiles'
        ]

    def upload(self, request):
        try:
            files = self.validated_data['files']
            infoFiles = self.validated_data['infoFiles']
            user_id = self.context['user_id']
            count = 0
            for item in files:
                print("item.file: ", item)
                print("item.info: ", infoFiles[count])  
    
                infoItem = infoFiles[count]
                infoItem = infoItem.split(';')
                display_file_name = infoItem[0]
                file_type = infoItem[1]
                size = infoItem[2]
                width = infoItem[3]
                height = infoItem[4]
                is_video = False
                thumb_video = None
                if infoItem[5] == "video":
                    is_video = True                    
                mediaModal = Media.objects.create(user_id=user_id, file=item, display_file_name=display_file_name, file_type=file_type, size=size, width=width, height=height, is_video=is_video, thumb_video=thumb_video) 
                if is_video and mediaModal:
                    try:
                        origin_path = get_s3_bucket_path(settings.AWS_STORAGE_BUCKET_NAME)
                        media_path = origin_path + str(mediaModal.file)
                        print("media_path: ", media_path)
                        # Read the video file using OpenCV
                        vidcap = cv2.VideoCapture(f"{media_path}")
                        # Extract the first frame of the video as a thumbnail
                        success,frame = vidcap.read()
                        thumbnail = Image.fromarray(frame)
                        # Resize the thumbnail image to the desired size
                        thumbnail_size = (300, 300)  # replace with your desired size
                        thumbnail.thumbnail(thumbnail_size, Image.ANTIALIAS)
                        # Convert the thumbnail image to bytes and upload it to S3
                        thumbnail_bytes = BytesIO()
                        thumbnail.save(thumbnail_bytes, format='JPEG')
                        thumbnail_bytes.seek(0)
                        s3 = boto3.client('s3')
                        s3.upload_fileobj(thumbnail_bytes, settings.AWS_STORAGE_BUCKET_NAME, f'{str(mediaModal.file)}.jpg')
                        s3.put_object_acl(ACL='public-read', Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=f'{str(mediaModal.file)}.jpg')
                        # Release the OpenCV resources
                        vidcap.release()
                        cv2.destroyAllWindows()
                        #
                        mediaModal = Media.objects.get(id=mediaModal.id, user_id=user_id)
                        thumb_video_path = f"{str(mediaModal.file)}.jpg"
                        mediaModal.thumb_video = thumb_video_path
                        mediaModal.save()                        
                    except Exception as err:
                        print("UploadImageLibrarySerializer_create_thumb_by_video_error: ", err)
                count += 1
            return True
        except Exception as e:
            print("Error",e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            fpath = os.path.split(exc_tb.tb_frame.f_code.co_filename)[0]
            print('ERROR', exc_type, fpath, fname, 'on line', exc_tb.tb_lineno)
            return False
        

class MediaSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=True)
    
    class Meta:
        model = Media
        fields = '__all__'

class MediaDeleteSerializer(serializers.ModelSerializer):
    ids = serializers.CharField(required=True)
    file_type = serializers.CharField(required=False)
    display_file_name = serializers.CharField(required=False)
    user = serializers.CharField(required=False)
    
    class Meta:
        model = Media
        fields = '__all__'
        extra_fields = ['ids']

    def delete(self, request):
        try:
            ids = str(self.validated_data['ids'])
            user_id = self.context['user_id']
            idsList = ids.split(',')            
            model = Media.objects.filter(id__in=idsList, user_id=user_id)            
            model.delete()
            return True
        except Exception as error:
            print("MediaSerializer_delete_error: ", error)
            return False
