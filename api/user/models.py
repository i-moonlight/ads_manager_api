from django.db import models

from django.contrib.auth.models import (
	AbstractBaseUser,
	BaseUserManager,
	PermissionsMixin,
)

import uuid

class UserManager(BaseUserManager):
	def create_user(self, username, email, password=None, **kwargs):
		"""Create and return a `User` with an email, username and password."""
		if username is None:
			raise TypeError("Users must have a username.")
		if email is None:
			raise TypeError("Users must have an email.")

		user = self.model(username=username, email=self.normalize_email(email))
		user.set_password(password)
		user.save(using=self._db)

		return user

	def create_superuser(self, username, email, password):
		"""
		Create and return a `User` with superuser (admin) permissions.
		"""
		if password is None:
			raise TypeError("Superusers must have a password.")
		if email is None:
			raise TypeError("Superusers must have an email.")
		if username is None:
			raise TypeError("Superusers must have an username.")

		user = self.create_user(username, email, password)
		user.is_superuser = True
		user.is_staff = True
		user.save(using=self._db)

		return user


class User(AbstractBaseUser, PermissionsMixin):
	username = models.CharField(db_index=True, max_length=255, unique=True)
	email = models.EmailField(db_index=True, null=True, blank=True)
	is_active = models.BooleanField(default=True)
	is_staff = models.BooleanField(default=False)
	date = models.DateTimeField(auto_now_add=True)
	last_login = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	first_name = models.CharField(max_length=150, default=None, null=True, blank=True)
	last_name = models.CharField(max_length=150, default=None, null=True, blank=True)
	display_name = models.CharField(max_length=150, default=None, null=True, blank=True)
	provider = models.CharField(max_length=150, default=None, null=True, blank=True)
	provider_id = models.CharField(max_length=150, default=None, null=True, blank=True)
	extra_data = models.TextField(default=None, null=True, blank=True)

	USERNAME_FIELD = "username"
	REQUIRED_FIELDS = ['email',]

	objects = UserManager()

	def __str__(self):
		return f"{self.username}"


def random_username(sender, instance, **kwargs):
    if not instance.username:
        instance.username = uuid.uuid4().hex[:30]
models.signals.pre_save.connect(random_username, sender=User)