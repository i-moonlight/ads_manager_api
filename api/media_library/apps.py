from django.apps import AppConfig

# https://www.appsloveworld.com/django/100/188/django-makemigrations-no-installed-app-with-label-appname
class MediaLibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.media_library"
    label = "api_media_library"
