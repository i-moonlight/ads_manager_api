from django.db import models
from ..user.models import User
from ..ad_manager.models import Campaigns, AdSets, Ads

# Create your models here.

class SnapchatCampaigns(models.Model):
	user = models.ForeignKey(User,on_delete = models.RESTRICT)
	campaign = models.ForeignKey(Campaigns,on_delete = models.RESTRICT)
	snapchat_campaign_id = models.CharField(max_length=50,null=False, blank=True)
	name = models.CharField(max_length=70,null=True)
	bid_strategy = models.CharField(max_length=50,null=True)
	lifetime_budget = models.IntegerField(null=True, blank=True)
	objective = models.TextField(null=True, blank=True)
	status = models.CharField(max_length=50,null=True)
	created = models.DateTimeField(auto_now_add=True, null=True)


class SnapchatCampaignsPerformance(models.Model):
	campaign = models.ForeignKey(Campaigns,on_delete = models.RESTRICT)
	snapchat_campaign = models.ForeignKey(SnapchatCampaigns,on_delete = models.RESTRICT)
	impressions = models.IntegerField(null=True, blank=True)
	clicks = models.IntegerField(null=True, blank=True)
	spend = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
	date = models.DateField(null=True)


class SnapchatAdSets(models.Model):
	user = models.ForeignKey(User,on_delete = models.RESTRICT)
	ad_set = models.ForeignKey(AdSets,on_delete = models.RESTRICT)
	snapchat_ad_set = models.CharField(max_length=80,null=False, blank=True)
	#more coming
	

class SnapchatAdSetsPerformance(models.Model):
	ad_set = models.ForeignKey(AdSets,on_delete = models.RESTRICT)
	snapchat_ad_set = models.ForeignKey(SnapchatAdSets,on_delete = models.RESTRICT)
	impressions = models.IntegerField(null=True, blank=True)
	clicks = models.IntegerField(null=True, blank=True)
	spend = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
	date = models.DateField(null=True)
	

class SnapchatAds(models.Model):
	user = models.ForeignKey(User,on_delete = models.RESTRICT)
	ad = models.ForeignKey(Ads,on_delete = models.RESTRICT)
	snapchat_ad = models.CharField(max_length=50,null=False, blank=True)
	# more to come


class SnapchatAdsPerformance(models.Model):
	ad = models.ForeignKey(Ads,on_delete = models.RESTRICT)
	snapchat_ad = models.ForeignKey(SnapchatAds,on_delete = models.RESTRICT)
	impressions = models.IntegerField(null=True, blank=True)
	clicks = models.IntegerField(null=True, blank=True)
	spend = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
	date = models.DateField(null=True)


