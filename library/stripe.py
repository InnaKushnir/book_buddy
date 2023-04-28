import os
import stripe
from flask import Flask, request, render_template_string

app = Flask(__name__)

stripe.api_key = "sk_test_51MdHRcCpjsnilJsOsmnyh2hIlV9Bac2c6qRcwbvs1YciV36XIgP4zqYMxaYBjLleBMXdYHaEKteet0WomHt6VTJ000fpDbvITT"


@app.route("/order/success", methods=["GET"])
def order_success(*args, **kwargs):
    session = stripe.checkout.Session.retrieve(request.args.get("session_id"))
    customer = stripe.Customer.retrieve(session.customer)

    return render_template_string(
        "<html><body><h1>Thanks for your order!</h1></body></html>", customer=customer
    )

    return "Success"


if __name__ == "__main__":
    app.run()
