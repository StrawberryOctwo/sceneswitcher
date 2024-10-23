from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError
from django.utils import timezone


class Package(models.Model):
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    stripe_id = models.CharField(max_length=200)
    video_limit = models.PositiveIntegerField()
    price_per_video = models.FloatField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class UserProfileManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('User must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class UserProfile(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True)
    credits = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    objects = UserProfileManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class UserPayment(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    payment_bool = models.BooleanField(default=False)
    stripe_checkout_id = models.CharField(max_length=500, null=True)
    stripe_customer_id = models.CharField(max_length=500, null=True)
    subscription_item_id = models.CharField(max_length=500, null=True)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    created = models.DateTimeField(default=timezone.now)

    @property
    def days_left(self):
        elapsed_days = (timezone.now() - self.created).days
        return max(30 - elapsed_days, 0)


class SingletonModel(models.Model):
    """Abstract base class that ensures only one instance of the model exists."""
    class Meta:
        abstract = True

    @classmethod
    def get_solo(cls):
        """Retrieve the single instance of the model."""
        if not cls.objects.exists():
            return cls()
        return cls.objects.first()

    def save(self, *args, **kwargs):
        """Override save method to ensure only one instance exists."""
        if self.pk is None and self.__class__.objects.exists():
            raise ValidationError(f"Cannot create more than one {self.__class__.__name__} instance.")
        return super().save(*args, **kwargs)


class StripeConfig(SingletonModel):
    STRIPE_SECRET_KEY = models.CharField(max_length=255, blank=False, null=False)
    STRIPE_WEBHOOK_SECRET = models.CharField(max_length=255, blank=False, null=False)
    STRIPE_REDIRECT_DOMAIN = models.URLField(default='http://0.0.0.0:8000')

    class Meta:
        verbose_name = "Stripe Configuration"
        verbose_name_plural = "Stripe Configurations"

    def __str__(self):
        return "Stripe Configuration"


class CustomCredit(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    credits = models.PositiveIntegerField()
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.email} - {self.credits} credits"

# import receiver to create a signal

from django.db.models.signals import post_save
from django.dispatch import receiver
# import cache

from django.core.cache import cache 
from uuid import uuid4
# send email
from django.core.mail import send_mail
from django.conf import settings

