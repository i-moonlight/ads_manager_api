from django.db import models


class Media(models.Model):
	user = models.ForeignKey("api_user.User", on_delete = models.RESTRICT)
	file = models.FileField(upload_to='media_files', null=True, blank=True)
	file_type = models.CharField(max_length=18)
	display_file_name = models.CharField(max_length=250)
	height = models.IntegerField(null=True, blank=True)
	width = models.IntegerField(null=True, blank=True)
	size = models.CharField(null=True, blank=True, max_length=255)
	uploaded = models.DateTimeField(auto_now_add=True)
	impressions = models.IntegerField(null=True, blank=True)
	clicks = models.IntegerField(null=True, blank=True)
	spent = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
	earned = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
	deactivated = models.BooleanField(null=True, blank=True)
	created = models.DateTimeField(auto_now_add=True)
	is_video = models.BooleanField(default=False)
	thumb_video = models.FileField(upload_to='media_files', null=True, blank=True)
	source = models.CharField(null=True, blank=True, max_length=32)
	original_file_name = models.CharField(null=True, blank=True, max_length=255)

	def __str__(self):
		return str(self.display_file_name)