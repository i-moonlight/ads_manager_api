from django.db import models

from ..user.models import User
from ..ad_manager.models import Campaigns, AdSets, Ads
from ..media_library.models import Media

# Create your models here.

class MetaLanguageLocales(models.Model):
	name = models.CharField(max_length=256,null=True)
	key = models.IntegerField(null=False)


