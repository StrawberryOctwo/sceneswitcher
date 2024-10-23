from django.contrib import admin
from .models import UserProfile, Package, StripeConfig, UserPayment


admin.site.register(UserProfile)
admin.site.register(Package)
admin.site.register(StripeConfig)
admin.site.register(UserPayment)
