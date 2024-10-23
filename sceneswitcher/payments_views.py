from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import UserPayment, Package, UserProfile, StripeConfig
from django.contrib.auth import login
import stripe
import time
import secrets
import string
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def purchase(request, package_id):
    stripe_config = StripeConfig.get_solo()
    package = Package.objects.get(pk=package_id)
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price": package.stripe_id,
                "quantity": 1,
            },
        ],
        mode="subscription",
        success_url=stripe_config.STRIPE_REDIRECT_DOMAIN
        + "/payment_successful?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=stripe_config.STRIPE_REDIRECT_DOMAIN + "/payment_cancelled",
    )
    return redirect(checkout_session.url, package_id=package_id, code=303)


def payment_successful(request, package_id=None):
    stripe_config = StripeConfig.get_solo()
    # stripe.api_key = stripe_config.STRIPE_SECRET_KEY
    checkout_session_id = request.GET.get("session_id", None)
    session = stripe.checkout.Session.retrieve(checkout_session_id)
    customer = stripe.Customer.retrieve(session.customer)
    email = customer.email
    characters = string.ascii_letters + string.digits + string.punctuation
    password = "".join(secrets.choice(characters) for _ in range(12))
    user = UserProfile.objects.create_user(email=email, password=password)
    login(request, user)
    user_payment = UserPayment.objects.get(stripe_checkout_id=checkout_session_id)
    package = user_payment.package
    user.package = package
    user.credits = package.video_limit
    user.save()
    user_payment.user = user
    user_payment.package = package
    user_payment.stripe_checkout_id = checkout_session_id
    user_payment.save()
    return render(request, "payments/payment_successful.html", {"password": password})


def payment_cancelled(request, package_id=None):
    stripe_config = StripeConfig.get_solo()
    # stripe.api_key = stripe_config.STRIPE_SECRET_KEY
    return render(request, "payments/payment_cancelled.html")


@csrf_exempt
def stripe_webhook(request):
    stripe_config = StripeConfig.get_solo()
    # stripe.api_key = stripe_config.STRIPE_SECRET_KEY
    time.sleep(10)
    payload = request.body
    signature_header = request.META["HTTP_STRIPE_SIGNATURE"]
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, signature_header, stripe_config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)
    session = event["data"]["object"]
    session_id = session.get("id", None)
    if event["type"] == "checkout.session.completed":
        time.sleep(15)
        user_payment = UserPayment.objects.get(stripe_checkout_id=session_id)
        user = user_payment.user
        user.credits = user_payment.package.video_limit
        user.save()
        user_payment.payment_bool = True
        user_payment.save()
    elif event["type"] == "customer.subscription.updated":
        user_payment = UserPayment.objects.get(stripe_checkout_id=session_id)
        user = user_payment.user
        user.credits = user_payment.package.video_limit
        user.save()
        user_payment.user.save()
    elif event["type"] == "customer.subscription.created":
        user_payment = UserPayment.objects.get(stripe_checkout_id=session_id)
        user = user_payment.user
        user.credits = user_payment.package.video_limit
        user.save()
    elif event["type"] == "customer.subscription.deleted":
        user_payment = UserPayment.objects.get(stripe_checkout_id=session_id)
        user_payment.payment_bool = False
        user = user_payment.user
        user.credits = 0
        user.save()
        user_payment.save()
    return HttpResponse(status=200)


import os
import json
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

import stripe
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from . import models
User = get_user_model()

def subscribe(request, plan_lookup) -> HttpResponse:
    return redirect(reverse('create-checkout-session') + f'?plan_lookup={plan_lookup}', code=303) 


def cancel(request) -> HttpResponse:
    return render(request, "payments/payment_cancelled.html")

from django.core.cache import cache
from uuid import uuid4

import time
def success(request) -> HttpResponse:
    checkout_session_id = request.GET.get("session_id", None)
    session = stripe.checkout.Session.retrieve(checkout_session_id)
    customer = stripe.Customer.retrieve(session.customer)
    email = customer.email
    counter = 0
    while True:
        counter += 1
        user = User.objects.filter(email=email).first()
        if user is not None:
            break
        time.sleep(4)
        if counter >= 3:
            return HttpResponse("Server error", status=500)
    if user.password != "":
        return redirect(reverse("login"))
    user_id = user.id
    token = str(uuid4())
    cache.set(token, user_id, timeout=86400)
    print("token", token)
    print("user_id", user_id)
    link = f"{settings.DOMAIN}/set-password?t={token}"
    context = {"set_password_url": link, "email": email}
    return render(request, "payments/payment_successful.html", context)


def create_checkout_session(request) -> HttpResponse:

    plan_lookup = request.GET.get('plan_lookup')
    try:
        di = {
            'basic': settings.BASIC_PRICE_ID,
            'professional': settings.PROFESSIONAL_PRICE_ID,
            'premium': settings.PREMIUM_PRICE_ID,
        }
        price_item = di[plan_lookup]

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {"price": price_item, "quantity": 1},
            ],
            mode="subscription",
            success_url=settings.DOMAIN
            + reverse("success")
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.DOMAIN + reverse("cancel"),
        )

        return redirect(
            checkout_session.url,  # Either the success or cancel url.
            code=303
        )
    except Exception as e:
        print(e)
        return HttpResponse("Server error", status=500)


def direct_to_customer_portal(request) -> HttpResponse:
    """
    Creates a customer portal for the user to manage their subscription.
    """
    # Get the last user payment record
    checkout_record = models.UserPayment.objects.filter(user=request.user).last()

    # Check if a checkout record exists
    if checkout_record is None:
        return HttpResponse("No payment record found.", status=404)

    try:

        # Create a billing portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=checkout_record.stripe_customer_id,
            return_url=f"{settings.DOMAIN}{reverse('subscription')}",  # Ensure full URL
        )

        # Redirect to the billing portal
        return redirect(portal_session.url, code=303)

    except stripe.error.StripeError as e:
        # Handle Stripe-specific errors
        return HttpResponse(f"Stripe error: {str(e)}", status=500)
    except Exception as e:
        # Handle other errors
        return HttpResponse(f"An error occurred: {str(e)}", status=500)


@csrf_exempt
def collect_stripe_webhook(request) -> JsonResponse:
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    signature = request.META["HTTP_STRIPE_SIGNATURE"]
    payload = request.body.decode('utf-8')

    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=signature, secret=webhook_secret
        )
    except ValueError as e:  # Invalid payload.
        raise ValueError(e)
    except stripe.error.SignatureVerificationError as e:  # Invalid signature
        raise stripe.error.SignatureVerificationError(e)
    email = None
    try:
        email = event['data']['object']['customer_email']
    except KeyError:
        pass 
        
    _update_record(event, email)
    return JsonResponse({'status': 'success'})


def _update_record(webhook_event, email) -> None:
    data_object = webhook_event['data']['object']
    event_type = webhook_event['type']
    if data_object.get('subscription') is None and event_type == 'checkout.session.completed' :
        amount = data_object['amount_total']
        email = data_object['customer_email']
        no_credit = amount // 5
        no_credit = no_credit / 100 
        user = models.UserProfile.objects.get(email=email)
        user.credits += no_credit
        models.CustomCredit.objects.create(user=user, credits=no_credit)
        user.save()
    
    elif event_type == "invoice.payment_succeeded":
        if data_object["lines"]["data"][0]["price"]["lookup_key"] == 'basic':
            credits = 25
        elif data_object["lines"]["data"][0]["price"]["lookup_key"] == 'professional':
            credits = 50
        elif data_object["lines"]["data"][0]["price"]["lookup_key"] == 'premium':
            credits = 100
        print("credits", credits)
        checkout_record, created = models.UserPayment.objects.get_or_create(
            stripe_checkout_id=data_object["subscription"], 
            package=models.Package.objects.get(video_limit=credits)
        )
        checkout_record.stripe_customer_id = data_object['customer']
        checkout_record.payment_bool = True
        checkout_record.save()
        if email is not None:
            name = data_object['customer_name'].split(' ')
            first_name, last_name = None, None
            if len(name) == 1:
                first_name = name[0]
            elif len(name) >= 2:
                first_name = name[0]
                last_name = name[1]
                
            user, created = models.UserProfile.objects.get_or_create(
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            if created:
                user.credits = credits
            else:
                user.credits += credits

            user.save()
            checkout_record.user = user
            checkout_record.save()
        
            

    elif event_type == 'customer.subscription.created':
        plan_lookup = data_object['items']['data'][0]['price']['lookup_key']
        id = data_object['id']
        if plan_lookup == "basic":
            package_id = 1
        elif plan_lookup == "professional":
            package_id = 2
        elif plan_lookup == "premium":
            package_id = 3
        package = models.Package.objects.get(id=package_id)
        obj, created = models.UserPayment.objects.get_or_create(
            stripe_checkout_id=id,
            package=package,
            
        )
        obj.subscription_item_id=webhook_event["data"]["object"]["items"]["data"][0][
                "id"
            ]
        obj.save()


@login_required
def downgrade_subscription(request, to):

    if to in ["basic", "professional"]:
        plan_lookup = to 
        current_subscription = UserPayment.objects.filter(user=request.user).last()
        if current_subscription is None:
            messages.error(request, "No active subscription found.")
            return redirect(reverse("subscription"))
        try:
            # Modify the subscription in Stripe
            prices = stripe.Price.list(lookup_keys=[plan_lookup], expand=['data.product'])
            price_item = prices.data[0]
            price_ids = {
                "basic": settings.BASIC_PRICE_ID,
                "professional": settings.PROFESSIONAL_PRICE_ID,
                "premium": settings.PREMIUM_PRICE_ID,
            }
            stripe.Subscription.modify(
                current_subscription.stripe_checkout_id,
                items=[
                    {
                        "id": current_subscription.subscription_item_id,
                        "price": price_ids[plan_lookup],
                    }
                ],
                proration_behavior="none",  # Prevent immediate charges; change at next billing
            )
            messages.error(request, f"Successfully downgraded to {to.capitalize()} plan.")
            return redirect(reverse("subscription"))
        except stripe.error.StripeError as e:

            messages.error(request, "Error Ocurred")
            return redirect(reverse("subscription"))
            # Handle Stripe API errors
    else:
        messages.error(request, "Invalid subscription type")
        return redirect(reverse("subscription"))

from django.contrib import messages
@login_required
def upgrade_subscription(request, to):
    if to in ["professional", "premium"]:
        plan_lookup = to
        current_subscription = UserPayment.objects.filter(user=request.user).last()
        if current_subscription is None:
            messages.error(request, "No active subscription found.")
            return redirect(reverse("subscription"))
        try:
            # Modify the subscription in Stripe
            prices = stripe.Price.list(
                lookup_keys=[plan_lookup], expand=["data.product"]
            )
            price_item = prices.data[0]
            price_ids = {
                "professional": settings.PROFESSIONAL_PRICE_ID,
                "premium": settings.PREMIUM_PRICE_ID,
                "basic": settings.BASIC_PRICE_ID,
            }
            stripe.Subscription.modify(
                current_subscription.stripe_checkout_id,
                items=[
                    {
                        "id": current_subscription.subscription_item_id,
                        "price": price_ids[plan_lookup],
                    }
                ],
                proration_behavior="none",  # Prevent immediate charges; change at next billing
            )
            messages.error(request, f"Successfully upgraded to {to.capitalize()} plan.")
            return redirect(reverse("subscription"))

        except stripe.error.StripeError as e:
            # Handle Stripe API errors

            messages.error(request, "Error Ocurred")
            return redirect(reverse("subscription"))
    else:
        messages.error(request, "Invalid subscription type")
        return redirect(reverse("subscription"))

@login_required
def cancel_subscription(request):
    current_subscription = UserPayment.objects.filter(user=request.user).last()
    if current_subscription is None:
        messages.error(request, "No active subscription found.")
        return redirect(reverse("subscription"))
    try:
        stripe.Subscription.delete(current_subscription.stripe_checkout_id)
        messages.error(request, "Subscription successfully cancelled.")
        return redirect(reverse("subscription"))
    except stripe.error.StripeError as e:
        # Handle Stripe API errors
        messages.error(request, "Error Ocurred")
        return redirect(reverse("subscription"))


@login_required
def buy_extra_credit(request):
    no_credits = request.GET.get('no_credits')
    print(no_credits)
    try:
        prices = stripe.Price.list(lookup_keys=['custom_credits'], expand=['data.product'])
        price_item = prices.data[0]

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {"price": price_item.id, "quantity": int(no_credits)},
            ],
            mode="payment",
            customer_email=request.user.email,
            success_url=settings.DOMAIN,
            cancel_url=settings.DOMAIN + reverse("cancel"),
        )

        return redirect(
            checkout_session.url,  # Either the success or cancel url.
            code=303
        )
    except Exception as e:
        print(e)
        return HttpResponse("Server error", status=500)


def confirm_page(request, action, plan):
    if request.method == "POST":
        if action == "upgrade":
            return redirect(reverse("upgrade_subscription", args=[plan]))
        elif action == "downgrade":
            return redirect(reverse("downgrade_subscription", args=[plan]))
        elif action == "cancel":
            return redirect(reverse("cancel_subscription"))

    return render(request, "payments/confirm.html", context={"action": action, "plan": plan})