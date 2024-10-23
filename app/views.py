from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from sceneswitcher.models import UserPayment, CustomCredit
def subscription_view(request):
    # Get the current plan of the with the latest created date and created in the last 30 days
    current_plan = UserPayment.objects.filter(user=request.user, created__gte=timezone.now() - timedelta(days=30)).last()
    if current_plan:
        current_plan_name = current_plan.package.name.lower()
        days_lift = current_plan.days_left
        all, used = 0, 0 
        userpayments = UserPayment.objects.filter(user=request.user, payment_bool=True)
        custom_credits = CustomCredit.objects.filter(user=request.user)
        for user_payment in userpayments:
            all += user_payment.package.video_limit
        for custom_credit in custom_credits:
            all += custom_credit.credits
        used = all - request.user.credits
        used_percentage = int(used / all * 100)
    else:
        return render(
            request,
            "subscription.html",
            context={
                "current_plan": "No plan",
                "days_lift": 0,
                "used": 0,
                "all": 0,
                "used_percentage": 0,
            },
        )
    return render(
        request,
        "subscription.html",
        context={
            "current_plan": current_plan_name,
            "days_lift": days_lift,
            "used": used,
            "all": all,
            "used_percentage": used_percentage,
        },
    )
