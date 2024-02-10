from django.db import models
from ..user.models import User
from ..media_library.models import Media

# Create your models here.

class Campaigns(models.Model):
	user = models.ForeignKey(User,on_delete = models.CASCADE, related_name='user_w_campaign')
	name = models.CharField(max_length=50,null=True)
	budget = models.IntegerField(null=True)
	daily_budget = models.IntegerField(null=True)
	start_date = models.DateField(null=True)
	end_date = models.DateField(null=True)
	credit = models.BooleanField(null=True)
	employment = models.BooleanField(null=True)
	housing = models.BooleanField(null=True)
	social = models.BooleanField(null=True)
	created = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=20,null=True)
	is_deleted = models.BooleanField(default=False)
	disabled = models.BooleanField(null=True)
	
	def __str__(self):
		return str(self.name)

class CampaignsPlatforms(models.Model):
	campaign = models.ForeignKey(Campaigns,on_delete = models.CASCADE, related_name='campaigns_platform')
	ad_platform = models.CharField(max_length=50, null=True)
	publisher_platform = models.CharField(max_length=50, null=True)
	api_id = models.CharField(max_length=50, null=True)
	disabled = models.BooleanField(null=True)
	status = models.CharField(max_length=20,null=True)
	previously_disabled = models.BooleanField(null=True)

class AdSets(models.Model):
	user = models.ForeignKey(User,on_delete = models.CASCADE, related_name='user_w_ad_sets')
	campaign = models.ForeignKey(Campaigns,on_delete = models.CASCADE, related_name='campaign_w_ad_sets')
	name = models.CharField(max_length=256,null=True)
	spend_limit = models.IntegerField(null=True)
	daily_budget = models.IntegerField(null=True)
	age_min = models.IntegerField(null=True)
	age_max = models.IntegerField(null=True)
	gender = models.CharField(max_length=20,null=True)
	created = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=20,null=True)
	is_deleted = models.BooleanField(default=False, null=True)
	disabled = models.BooleanField(null=True)
	 
	def __str__(self):
		return str(self.name) + '(' + self.campaign.name + ')'


class AdSetsPlatforms(models.Model):
	ad_set = models.ForeignKey(AdSets,on_delete = models.CASCADE, related_name='ad_sets_platform')
	ad_platform = models.CharField(max_length=50, null=True)
	publisher_platform = models.CharField(max_length=50, null=True)
	api_id = models.CharField(max_length=50, null=True)
	disabled = models.BooleanField(null=True)
	status = models.CharField(max_length=20,null=True)
	previously_disabled = models.BooleanField(null=True)


class AdSetsKeywords(models.Model):
	ad_set = models.ForeignKey(AdSets,on_delete = models.CASCADE, related_name='keywords_w_ad_set')
	keyword = models.CharField(max_length=100)
	created = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return str(self.ad_set.name + '(' + self.keyword + ')')
	

class AdSetsLanguages(models.Model):
	ad_set = models.ForeignKey(AdSets,on_delete = models.CASCADE, related_name='languages_w_ad_set')
	language = models.CharField(max_length=100,null=True)
	created = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return str(self.ad_set.name + '(' + self.language + ')') + ", " + self.ad_set.campaign.name


class AdSetsLocations(models.Model):
	ad_set = models.ForeignKey(AdSets,on_delete = models.CASCADE, related_name='locations_w_ad_set')
	location = models.CharField(max_length=50, null=True)
	gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True)
	gps_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True)
	radius = models.IntegerField(null=True, blank=True)
	distance_unit = models.CharField(max_length=10, default='mile', null=True)
	created = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return str(self.ad_set.name+ '(' + self.location + ')')

class AdSetsJobTitles(models.Model):
	ad_set = models.ForeignKey(AdSets,on_delete = models.CASCADE, related_name='job_titles_w_ad_set')
	name = models.CharField(max_length=255, null=True)

	def __str__(self):
		return str(self.ad_set.name + '(' + self.name + ')')

class Ads(models.Model):
	user = models.ForeignKey(User,on_delete = models.CASCADE, related_name='user_w_ads')
	campaign = models.ForeignKey(Campaigns,on_delete = models.CASCADE, related_name='campaign_w_ads')
	ad_set = models.ForeignKey(AdSets,on_delete = models.CASCADE, related_name='ad_set_w_ads')
	name = models.CharField(max_length=50)
	media = models.ForeignKey(Media,on_delete = models.CASCADE,null=True, related_name='media_w_ads')
	thumbnail = models.FileField(upload_to='thumbs', null=True, blank=True)
	destination_url = models.CharField(max_length=512,null=True)
	display_url = models.CharField(max_length=512,null=True, blank=True)
	call_to_action_linkedin = models.CharField(max_length=128,null=True)
	call_to_action_meta = models.CharField(max_length=128,null=True)
	call_to_action_snapchat = models.CharField(max_length=128,null=True)
	call_to_action_tiktok = models.CharField(max_length=128,null=True)
	headline = models.CharField(max_length=24,null=True)
	primary_text = models.CharField(max_length=125,null=True)
	description = models.CharField(max_length=27,null=True)
	facebook_page = models.CharField(max_length=64,null=True)
	facebook_page_id = models.CharField(max_length=64,null=True)
	instagram_account = models.CharField(max_length=64,null=True)
	instagram_account_id = models.CharField(max_length=64,null=True)
	pinterest_board = models.CharField(max_length=64,null=True)
	pinterest_board_id = models.CharField(max_length=64,null=True)
	brand_name= models.CharField(max_length=30,null=True)
	ad_created_at = models.DateField(null=True, blank=True)
	created = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=20,null=True)
	disabled = models.BooleanField(null=True)
	is_deleted = models.BooleanField(default=False)

	def __str__(self):
		return str(self.name + '(' + self.ad_set.name + ', ' + self.campaign.name + ')')


class AdsPerformance(models.Model):
	ad = models.ForeignKey(Ads,on_delete = models.CASCADE, related_name='ads_performance')
	ad_platform = models.CharField(max_length=50, null=True)
	publisher_platform = models.CharField(max_length=50, null=True)
	impressions = models.IntegerField(null=True, blank=True)
	clicks = models.IntegerField(null=True, blank=True)
	actions = models.IntegerField(null=True, blank=True)
	spend = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
	earned = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
	date = models.DateField(null=True)
	status = models.CharField(max_length=20,null=True)
	disabled = models.BooleanField(null=True)

	def __str__(self):
		return str(self.ad.name + '(' + self.ad_platform + ')' )

class AdsPlatforms(models.Model):
	ad = models.ForeignKey(Ads,on_delete = models.CASCADE, related_name='ads_platform')
	ad_platform = models.CharField(max_length=50, null=True)
	publisher_platform = models.CharField(max_length=50, null=True)
	api_id = models.CharField(max_length=50, null=True)
	disabled = models.BooleanField(null=True)
	status = models.CharField(max_length=20,null=True)
	run_on = models.BooleanField(default=True)
	previously_disabled = models.BooleanField(null=True)

