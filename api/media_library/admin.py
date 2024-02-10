from django.contrib import admin
from django.apps import apps

# https://codinggear.blog/how-to-register-model-in-django-admin/
# https://stackoverflow.com/questions/10769987/django-admin-site-register-doesnt-add-my-app-admin
media_library_models = apps.get_app_config('api_media_library').get_models()

for model in media_library_models:
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass