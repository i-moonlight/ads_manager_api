from django.db import models

class Contact(models.Model):
  email = models.EmailField()
  comment = models.TextField()
  date = models.DateTimeField(auto_now_add=True)
  ip_address = models.GenericIPAddressField(null=True)

  def __str__(self):
    return self.email
