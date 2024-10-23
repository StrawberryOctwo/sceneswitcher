from django.contrib import admin
from django.urls import path
from .views import *
from .payments_views import (
    purchase,
    payment_successful,
    payment_cancelled,
    stripe_webhook,
    subscribe,
    cancel,
    success,
    create_checkout_session,
    direct_to_customer_portal,
    collect_stripe_webhook,
    downgrade_subscription,
    upgrade_subscription,
    cancel_subscription,
    confirm_page
)
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("", index, name="index"),
    path("app", app, name="app"),
    path("video_processing", video_processing_page, name="video_processing"),
    path("process_video", process_video, name="process_video"),
    path("process", process, name="process"),
    path("uploads/<str:file_name>", load_media_file, name="load_media"),
    path("final_video/<str:file_name>", load_final_media_file, name="load_final_media"),
    path("get_srt_index", get_srt_index, name="get_srt_index"),
    path("download", download, name="download"),
    path("upload_new_scene", upload_new_scene, name="upload_new_scene"),
    # stripe payments
    path("purchase/<int:package_id>", purchase, name="purchase"),
    path("payment_successful", payment_successful, name="payment_successful"),
    path("payment_cancelled", payment_cancelled, name="payment_cancelled"),
    path("stripe_webhook", stripe_webhook, name="stripe_webhook"),
    # new urls
    path("set-password/", set_password, name="set_password"),
    path("subscribe/<str:plan_lookup>", subscribe, name="subscribe"),
    path("cancel/", cancel, name="cancel"),
    path("success/", success, name="success"),
    path(
        "create-checkout-session/",
        create_checkout_session,
        name="create-checkout-session",
    ),
    path(
        "direct-to-customer-portal/",
        direct_to_customer_portal,
        name="direct-to-customer-portal",
    ),
    path(
        "collect-stripe-webhook/", collect_stripe_webhook, name="collect-stripe-webhook"
    ),
    path("downgrade/<str:to>", downgrade_subscription, name="downgrade_subscription"),
    path("upgrade/<str:to>", upgrade_subscription, name="upgrade_subscription"),
    path("cancel-subscription/", cancel_subscription, name="cancel_subscription"),
    path("confirm/<str:action>/<str:plan>", confirm_page, name="confirm"),
    path('password-reset/', 
        auth_views.PasswordResetView.as_view(
            template_name='registration/reset_password.html',
            email_template_name='password_reset_email_template.html'

        ), 
        name='password_reset'),
        
    path('password-reset/done/', 
        auth_views.PasswordResetDoneView.as_view(
            template_name='password_reset_done.html'
        ), 
        name='password_reset_done'),

    path('reset/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(
            template_name='password_reset_confirm.html'
        ), 
        name='password_reset_confirm'),

    path('reset/done/', 
        auth_views.PasswordResetCompleteView.as_view(
            template_name='password_reset_complete.html'
        ), 
        name='password_reset_complete'),
]
