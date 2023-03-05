import os

import stripe


stripe.api_key = "sk_test_51MdHRcCpjsnilJsOsmnyh2hIlV9Bac2c6qRcwbvs1YciV36XIgP4zqYMxaYBjLleBMXdYHaEKteet0WomHt6VTJ000fpDbvITT"

def checkout_session(request, money):

    checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(1 * 100),
                        "product_data": borrowing.book.title
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url="http://127.0.0.1:8000/library/borrowings/",
            cancel_url="http://127.0.0.1:8000/library/borrowings/",
        )
    session_id = checkout_session.id
    session_url = checkout_session.url

    return redirect(checkout_session.url, code=303)
