from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from .views import subscription_view
from sceneswitcher.payments_views import buy_extra_credit

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("sceneswitcher.urls")),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("subscription/", subscription_view, name="subscription"),
    path('buy_extra_credit/', buy_extra_credit, name='buy-extra-credit'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
