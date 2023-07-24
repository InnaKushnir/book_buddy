import os

import stripe
from django.http import HttpResponse
from rest_framework.decorators import api_view


@api_view(["GET"])
def order_success(*args, **kwargs):
    session = stripe.checkout.Session.retrieve(request.GET.get("session_id"))
    customer = stripe.Customer.retrieve(session.customer)

    return HttpResponse("Success")
