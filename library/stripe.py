import os
from django.conf import settings
import stripe


stripe.api_key = settings.STRIPE_SECRET_KEY


def checkout_session(product_id, price_id):
    # Create a new session in Stripe
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price": price_id,
                "product": product_id,
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )

    # Return the session ID
    return session.id
