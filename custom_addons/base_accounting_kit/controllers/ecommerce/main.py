from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import ValidationError
from werkzeug.urls import url_parse, url_decode
import ast
from werkzeug.exceptions import NotFound, UnprocessableEntity
import os
from werkzeug.utils import redirect
import hmac
import hashlib
import base64
import uuid
from .utils import SendMail
import json
import requests
from odoo import fields
from collections import defaultdict
from datetime import datetime
import nepali_datetime
from .utils import NepalTZ

ESEWA_PRODUCT_KEY = os.getenv("ESEWA_PRODUCT_KEY", "EPAYTEST")
ESEWA_CLIENT_KEY = os.getenv("ESEWA_CLIENT_KEY", "8gBm/:&EnhH.1/q")
STATUS_TEST_URL = "https://epay.esewa.com.np/api/epay/transaction/status/"

KHALTI_STATIC_API = os.getenv("KHALTI_STATIC_API", False)
KHALTI_SECRET_KEY = os.getenv("KHALTI_SECRET_KEY", False)
KHALTI_LOOKUP_URL = os.getenv("KHALTI_LOOKUP_URL", False)
MAIN_DOMAIN_URL = os.getenv("ECOMMERCE_MAIN_DOMAIN", "http://lekhaplus.com/")


class CheckoutController(http.Controller):

    @http.route(["/get_checkout_confirmation"], type="json", csrf=False, auth="user")
    def get_checkout_confirmation(self, **kwargs):
        try:
            order_ids = kwargs.get("order_id", [])
            price_breakdown = json.loads(kwargs.get("price_breakdown", []))

            shipping_address_master = (
                request.env["ecommerce.user.address"]
                .sudo()
                .get_default_address("shipping", request.env.user.id)
            )
            billing_address_master = (
                request.env["ecommerce.user.address"]
                .sudo()
                .get_default_address("billing", request.env.user.id)
            )
            pickup_type = kwargs.get("pickup_type", "shipping")
            shipping_address = ""
            if pickup_type == "shipping":
                shipping_address = f""" <p>
                                    <strong>{_('Shipping:')} <br/>
                                    <strong>{shipping_address_master.fullname} {shipping_address_master.phone_number}</strong>
                                    <br/>
                                    <strong>{shipping_address_master.address} {shipping_address_master.street}</strong>
                                </p>"""
            else:
                shipping_address = "Onsite Pickup"

            billing_address = f""" <p>
                                <strong>{_('Billing:')} <br/>
                                <strong>{billing_address_master.fullname} {billing_address_master.phone_number}</strong>
                                <br/>
                                <strong>{billing_address_master.address} {billing_address_master.street}</strong>
                              </p>"""

            if isinstance(order_ids, str):
                order_ids = ast.literal_eval(order_ids)
            checkout_order = (
                request.env["ecommerce.checkout"]
                .sudo()
                .create(
                    {
                        "user_id": request.env.user.id,
                        "price_total": float(kwargs.get("total_amt", 1000)),
                        "cart_item_ids": [(6, 0, order_ids)],
                        "billing_address": billing_address,
                        "pickup_type": pickup_type,
                        "pickup_address": shipping_address,
                        "status": "active",
                    }
                )
            )
            host_url = request.httprequest.host_url

            decoded_url = url_parse(
                f"{host_url}checkout/order-id={checkout_order.checkout_order_token}"
            )
            redirect_url = decoded_url.to_url()
            request.session.update(
                {
                    "price_breakdown": price_breakdown,
                    "order_ids": order_ids,
                }
            )
            return {"success": True, "data": redirect_url}
        except Exception as e:
            return {"success": False, "message": e}

    @http.route(
        ["/checkout/order-id=<string:checkout_order_token>"],
        type="http",
        website=True,
        auth="user",
        csrf=False,
    )
    def get_payment_providers_page(self, checkout_order_token, **kwargs):
        try:

            checkout_order = (
                request.env["ecommerce.checkout"]
                .sudo()
                .search(
                    [
                        ("user_id", "=", request.env.user.id),
                        ("checkout_order_token", "=", checkout_order_token),
                        ("status", "=", "active"),
                    ],
                    limit=1,
                )
            )

            if not checkout_order:
                return request.redirect("/not-found")
            return request.render(
                "base_accounting_kit.select_payment_method",
                {
                    "checkout_order": checkout_order,
                },
            )
        except Exception as e:
            print(e)
            raise ValidationError(_("SOmething went wrong"))

    @http.route(["/get_extra_fees"], type="json", csrf=False, auth="user")
    def get_extra_fees(self, **kwargs):
        try:
            type = kwargs.get("type", "cod")
            extra_charge = (
                request.env["ecommerce.payment.charges"]
                .sudo()
                .search([("fee", ">", 0), ("payment_method.code", "=", type)])
            )
            total_extra_price = 0
            for ec in extra_charge:
                total_extra_price += ec.fee

            options = {
                "extra_charge": extra_charge,
            }
            data = {
                "ui": request.env["ir.ui.view"]._render_template(
                    "base_accounting_kit.payment_extra_fees", options
                ),
                "total_extra_price": total_extra_price,
            }
            return {
                "success": True,
                "data": data,
            }
        except Exception as e:
            return {
                "success": False,
                "message": e,
            }

    @http.route(["/order_now"], type="json", csrf=False, auth="user")
    def order_now(self, **kwargs):
        try:
            extra_charges_dict = kwargs.get("extra_charges", {})
            data = {
                "order_id": kwargs.get("order_id", ""),
                "t_amt": kwargs.get("t_amt", 0),
                "extra_charges": kwargs.get("extra_charges", {}),
                "payment_method": kwargs.get("payment_method", "cod"),
                "charges_title": extra_charges_dict.get("charges_title", []),
            }
            result = self.confirmed_order(data)

            if result.get("success", False):
                return {
                    "success": True,
                    "success_url": result.get("success_url"),
                    "message": _("The order has been placed successfully."),
                }
            else:
                return {"success": False, "message": result.get("message", "")}

        except Exception as e:
            return {"success": False, "message": e}

    @http.route(
        ["/my-orders/order-success=<string:common_order_token>"],
        website=True,
        auth="user",
        type="http",
    )
    def order_success(self, common_order_token):
        user = request.env.user
        my_order = (
            request.env["ecommerce.orders"]
            .sudo()
            .get_my_order(common_order_token, user.id)
        )
        if not my_order:
            return redirect("/not-found")

        address = (
            request.env["res.partner"]
            .sudo()
            .get_default_address("billing", user.commercial_partner_id.id)
        )
        return request.render(
            "base_accounting_kit.order_placed_successfully",
            {"my_orders": my_order, "address": address},
        )

    def cancel_sales_order(self):
        pass

    @http.route(
        ["/ecommerce_esewa_payment_redirect"], type="json", csrf=False, auth="user"
    )
    def ecommerce_esewa_payment_redirect(self, **data):
        base_url = request.httprequest.host_url
        order_token = data.get("order_token", "")
        extra_charges = data.get("extra_charges", {})
        total_extra_amt = extra_charges.get("total_extra_amt", 0)
        tAmt = data.get("t_amt", 0)

        pid = str(uuid.uuid4().int)

        checkout_order = (
            request.env["ecommerce.checkout"]
            .sudo()
            .search([("checkout_order_token", "=", order_token)])
            .update({"payment_token": pid})
        )
        try:

            message = f"total_amount={float(tAmt)},transaction_uuid={pid},product_code={ESEWA_PRODUCT_KEY}"

            secret = ESEWA_CLIENT_KEY
            hash_bytes = hmac.new(
                secret.encode(), message.encode(), hashlib.sha256
            ).digest()

            hash_in_base64 = base64.b64encode(hash_bytes).decode()

            payment_details = {
                "pid": pid,
                "tAmt": float(tAmt),
                "scd": ESEWA_PRODUCT_KEY,
                "su": f"{base_url}/esewa_payment_success_lookup",
                "fu": f"{base_url}/ecommerce_esewa_payment_failure",
                "delivery_charge": float(total_extra_amt),
                "hash_in_base64": hash_in_base64,
            }

            esewa_payment_template = request.env["ir.ui.view"]._render_template(
                "base_accounting_kit.esewa_payment_form",
                {"payment_details": payment_details},
            )
            request.session.update(
                {
                    "order_id": order_token,
                    "t_amt": data.get("t_amt", 0),
                    "extra_charges": extra_charges,
                    "payment_method": data.get("payment_method", "esewa"),
                }
            )
            return {"success": True, "data": esewa_payment_template}
        except Exception as e:
            return {"success": False, "message": e}

    @http.route("/test_email", type="http", auth="public", website=True)
    def test_email(self):
        orders = (
            request.env["ecommerce.orders"]
            .sudo()
            .get_my_order("288741049432630444973422641837", request.env.user.id)
        )
        return request.render(
            "base_accounting_kit.order_confirmed_email", {"orders": orders}
        )

    @http.route(
        "/esewa_payment_success_lookup",
        type="http",
        auth="public",
        # methods=["POST"],
        csrf=False,
        save_session=True,
    )
    def esewa_payment_success_lookup(self, **data):
        base64_encoded_str = data.get("data", "")
        decoded_bytes = base64.b64decode(base64_encoded_str)
        decoded_str = decoded_bytes.decode("utf-8")
        decoded_data = json.loads(decoded_str)

        transaction_uuid = decoded_data.get("transaction_uuid")
        order_checkout = (
            request.env["ecommerce.checkout"]
            .sudo()
            .search(
                [
                    ("payment_token", "=", transaction_uuid),
                ],
                limit=1,
            )
        )
        if not order_checkout:
            redirect_url = f"{request.httprequest.host_url}my/cart"
            request.session.update(
                {
                    "redirect_url": redirect_url,
                }
            )
            return request.redirect(f"/bad-request?spam={str(uuid.uuid4())}")
        url = STATUS_TEST_URL

        d = {
            "product_code": ESEWA_PRODUCT_KEY,
            "transaction_uuid": transaction_uuid,
            "total_amount": decoded_data.get("total_amount"),
        }
        base_url = request.httprequest.host_url
        try:
            resp = requests.get(url, params=d)
            json_resp_data = resp.json()
            resp.raise_for_status()
        except Exception as e:
            print(f"Error during the request to eSewa: {e}")
            return request.redirect(f"{base_url}payment-failure")

        if resp.status_code == 200 and json_resp_data.get("status") == "COMPLETE":
            data = {
                "order_id": request.session.get("order_id", ""),
                "t_amt": request.session.get("t_amt", 0),
                "extra_charges": request.session.get("extra_charges", {}),
                "payment_method": request.session.get("payment_method", "esewa"),
            }
            self.confirmed_order(data)
            return request.redirect("/my-orders")

        else:
            redirect_url = f"{request.httprequest.host_url}checkout/order-id={order_checkout.checkout_order_token}"
            request.session.update(
                {
                    "redirect_url": redirect_url,
                }
            )
            return request.redirect(f"/bad-request?spam={str(uuid.uuid4())}")

    @http.route(
        "/ecommerce_esewa_payment_failure",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def ecommerce_esewa_payment_failure(self, **data):
        try:
            return request.redirect("/payment-failure")

        except Exception as e:
            print("ecommerce_esewa_payment_successful error", e)
            raise ValidationError(
                f'{_("Unexpected error occurred, please navigate to the invoice bill manually. We are sorry for the inconvenience!")}- [{e}]'
            )

    @http.route(
        "/ecommerce_khalti_initiate",
        type="json",
        auth="user",
        csrf=False,
    )
    def initiate_khalti(self, **data):
        base_url = request.httprequest.host_url
        order_token = data.get("order_id", "")
        extra_charges = data.get("extra_charges", {})

        order_checkout = (
            request.env["ecommerce.checkout"]
            .sudo()
            .search([("checkout_order_token", "=", order_token)], limit=1)
        )

        if not order_checkout:
            raise ValidationError(_("Invalid Order"))

        tAmt = data.get("t_amt", 0)

        url = KHALTI_STATIC_API
        key = KHALTI_SECRET_KEY
        if not url and not key and not KHALTI_LOOKUP_URL:
            raise ValidationError(
                _("The e-commerce khalti payment gateway is not configured!!")
            )
        address = request.env["ecommerce.user.address"].get_addresses(
            order_checkout.user_id.id, "invoicing"
        )
        if address:
            name = address.fullname
            email = address.email
            phone = address.phone_number
        else:
            name = request.env.user.name
            email = request.env.user.login
            phone = request.env.user.mobile

        payload = json.dumps(
            {
                "return_url": base_url + "ecommerce_khalti_verify/",
                "website_url": base_url,
                "amount": int(tAmt * 100),
                "purchase_order_id": order_token,
                "purchase_order_name": "Order Payment",
                "customer_info": {
                    "name": name,
                    "email": email,
                    "phone": phone,
                },
            }
        )

        headers = {
            "Authorization": f"key {key}",
            "Content-Type": "application/json",
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        resp_text = response.text
        response_dict = json.loads(resp_text)

        if response.status_code == 200:
            payment_url = response_dict["payment_url"]
            decoded_url = url_parse(payment_url)
            args = url_decode(decoded_url.query)
            payment_token = args.get("pidx")

            order_checkout.write({"payment_token": payment_token})
            request.session.update(
                {
                    "order_id": order_token,
                    "t_amt": tAmt,
                    "extra_charges": extra_charges,
                    "payment_method": data.get("payment_method", "khalti"),
                }
            )

            return {
                "success": True,
                "data": payment_url,
            }
        else:
            print("Error detail", response_dict["detail"])
            print("Error code", response_dict["error_key"])
            return {"success": False, "message": response_dict["detail"]}

    @http.route(
        "/ecommerce_khalti_verify",
        type="http",
        auth="user",
        website=True,
        csrf=False,
        save_session=True,
    )
    def ecommerce_khalti_verify(self, **data):

        url = KHALTI_LOOKUP_URL
        pidx = data.get("pidx")
        order_checkout = (
            request.env["ecommerce.checkout"]
            .sudo()
            .search(
                [
                    ("user_id", "=", request.env.user.id),
                    ("payment_token", "=", pidx),
                ],
                limit=1,
            )
        )
        payload = json.dumps({"pidx": pidx})
        headers = {
            "Authorization": f"key {KHALTI_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            resp_text = response.text
            response_dict = json.loads(resp_text)
            if response_dict["status"] == "Completed":
                data = {
                    "order_id": request.session.get("order_id", ""),
                    "t_amt": request.session.get("t_amt", 0),
                    "extra_charges": request.session.get("extra_charges", {}),
                    "payment_method": request.session.get("payment_method", "khalti"),
                }
                self.confirmed_order(data)

        else:
            redirect_url = f"{request.httprequest.host_url}my/cart"
            request.session.update(
                {
                    "redirect_url": redirect_url,
                }
            )
            return request.redirect(f"/bad-request?spam={str(uuid.uuid4())}")

    @http.route("/confirmed_order", type="json", auth="user")
    def confirmed_order(self, data):
        try:
            order_id = data.get("order_id", "")
            t_amt = data.get("t_amt", 0)
            extra_charges_dict = data.get("extra_charges", {})
            payment_method = data.get("payment_method", "cod")

            charges_title_list = extra_charges_dict.get("charges_title", [])
            charges_title_body = ""
            for charge in charges_title_list:
                charges_title_body += f"<li>{charge}</li>"
            charges_title = f"""
            <ul>
                {charges_title_body}
            </ul>
            """
            charges_total_amt = extra_charges_dict.get("total_extra_amt", 0)

            checkout_order = request.env["ecommerce.checkout"].sudo()
            if not checkout_order.search(
                [
                    ("checkout_order_token", "=", order_id),
                    ("user_id", "=", request.env.user.id),
                ]
            ):
                return {"success": False, "message": _("Invalid Order")}
            elif not checkout_order.search(
                [
                    ("checkout_order_token", "=", order_id),
                    ("price_total", "=", float(t_amt) - float(charges_total_amt)),
                    ("user_id", "=", request.env.user.id),
                ]
            ):
                return {"success": False, "message": _("The order price is invalid.")}

            try:
                order_line_id = checkout_order.search(
                    [
                        ("checkout_order_token", "=", order_id),
                        ("user_id", "=", request.env.user.id),
                    ],
                    limit=1,
                )
                carts_ids = order_line_id.cart_item_ids
                order = request.env["ecommerce.orders"].sudo()
                payment_status = "unpaid"
                if payment_method != "cod":
                    payment_status = "paid"

                common_token = str(uuid.uuid4())

                # Create new_orders from carts_ids
                new_orders = []
                for carts_id in carts_ids:
                    new_order = order.create(
                        {
                            "user": request.env.user.id,
                            "status": "pending",
                            "order_line_ids": carts_id.id,
                            "extra_charge": float(charges_total_amt),
                            "extra_charge_title": charges_title,
                            "total_amount": t_amt,
                            "payment_method": payment_method,
                            "payment_status": payment_status,
                            "order_common_token": common_token,
                        }
                    )
                    activity_payload = {
                        "user_id": request.env.user.id,
                        "product_id": carts_id.product_id.id,
                        "activity_type": "purchase",
                    }

                    requests.post(
                        f"{MAIN_DOMAIN_URL}create_user_purchase_activity",
                        json=activity_payload,
                        headers={"Content-Type": "application/json"},
                    )

                    new_orders.append(new_order)

                # Deactivate carts
                request.env["ecommerce.add.to.cart"].sudo().deactivate_cart(
                    carts_ids.ids
                )

                # Update order_line_id status
                order_line_id.write({"status": "purchased"})

                # Group new_orders by partner_id (Vendor)
                grouped_orders = defaultdict(list)
                for order in new_orders:
                    # Get the partner_id from the cart linked to the order_line_ids
                    cart_id = (
                        request.env["ecommerce.add.to.cart"]
                        .sudo()
                        .browse(order.order_line_ids.ids)
                    )
                    partner_id = (
                        cart_id.product_id.company_id.partner_id.id
                    )  # Assuming the vendor is linked to the company
                    grouped_orders[partner_id].append(order)

                # Process each group of orders
                for partner_id, orders in grouped_orders.items():
                    # Use the first order in the group for common details
                    first_order = orders[0]
                    # Fetch user and partner details
                    user_id = first_order.user.id
                    if not user_id:
                        raise ValueError("User must be specified for an order.")

                    user_partner = (
                        request.env["res.users"]
                        .sudo()
                        .browse(user_id)
                        .commercial_partner_id
                    )

                    # Fetch invoice and shipping addresses
                    address = request.env["res.partner"].sudo()
                    invoice_address = address.get_default_address(
                        "billing", user_partner.id
                    )
                    shipping_address = address.get_default_address(
                        "shipping", user_partner.id
                    )

                    # Prepare the sale order values
                    sale_order_vals = {
                        "company_id": cart_id.product_id.company_id.id,  # Use cart_id to get company_id
                        "partner_id": user_partner.id,
                        "date_order": first_order.order_date
                        or NepalTZ.get_nepal_time(),
                        "partner_invoice_id": (
                            invoice_address.id if invoice_address else None
                        ),
                        "partner_shipping_id": (
                            shipping_address.id if shipping_address else None
                        ),
                    }

                    # Create the sale order
                    sale_order = (
                        request.env["sale.order"].sudo().create(sale_order_vals)
                    )

                    # Add order lines from each order in the group to the sale order
                    for order in orders:
                        order_line_ids = (
                            request.env["ecommerce.add.to.cart"]
                            .sudo()
                            .browse(order.order_line_ids.ids)
                            .read(
                                [
                                    "product_id",
                                    "quantity",
                                    "price_unit",
                                    "subtotal",
                                    "cart_attribute_ids",
                                ]
                            )
                        )
                        for line in order_line_ids:
                            product_id = line.get("product_id")
                            if isinstance(product_id, tuple):
                                product_id_value = product_id[0]
                            else:
                                product_id_value = product_id
                            product_custom_price = (
                                request.env["product.custom.price"]
                                .sudo()
                                .search(
                                    [
                                        ("id", "=", product_id_value),
                                    ],
                                    limit=1,
                                )
                            )
                            if product_custom_price and product_custom_price.product_id:
                                product_product_id = (
                                    product_custom_price.product_id.product_variant_id.id
                                )
                                product_template_id = product_custom_price.product_id
                            else:
                                product_product_id = None
                                product_template_id = None

                            attribute_id = line.get("cart_attribute_ids")
                            attributes = (
                                request.env["ecommerce.cart.attributes"]
                                .sudo()
                                .browse(attribute_id)
                                .read(["cart_id", "attribute_id", "value_id"])
                            )

                            attribute_value_ids = []
                            for attribute in attributes:
                                attribute_name = (
                                    attribute.get("attribute_id")[1]
                                    if attribute.get("attribute_id")
                                    else None
                                )
                                value_name = (
                                    attribute.get("value_id")[1]
                                    if attribute.get("value_id")
                                    else None
                                )
                                if ":" in value_name:
                                    value_name = value_name.split(":")[1].strip()
                                if not attribute_name or not value_name:
                                    continue

                                product_attribute = (
                                    request.env["product.attribute"]
                                    .sudo()
                                    .search([("name", "=", attribute_name)], limit=1)
                                )
                                if not product_attribute:
                                    continue

                                product_attribute_value = (
                                    request.env["product.attribute.value"]
                                    .sudo()
                                    .search(
                                        [
                                            ("name", "=", value_name),
                                            ("attribute_id", "=", product_attribute.id),
                                        ],
                                        limit=1,
                                    )
                                )

                                if product_attribute_value:
                                    attribute_value_ids.append(
                                        product_attribute_value.id
                                    )
                                else:
                                    print(
                                        f"Attribute Value '{value_name}' not found for Attribute '{attribute_name}', skipping."
                                    )

                            if product_template_id and attribute_value_ids:
                                product_variant = (
                                    request.env["product.product"]
                                    .sudo()
                                    .search(
                                        [
                                            (
                                                "product_tmpl_id",
                                                "=",
                                                product_template_id.id,
                                            ),
                                            (
                                                "product_template_attribute_value_ids.product_attribute_value_id",
                                                "in",
                                                attribute_value_ids,
                                            ),
                                        ],
                                        limit=1,
                                    )
                                )

                                if product_variant:
                                    product_product_id = product_variant.id

                            sale_order_line_vals = {
                                "order_id": sale_order.id,
                                "product_id": product_product_id,
                                "product_uom_qty": line.get("quantity"),
                                "price_unit": line.get("price_unit"),
                                "price_subtotal": line.get("subtotal"),
                                "tax_id": False,
                            }
                            request.env["sale.order.line"].sudo().create(
                                sale_order_line_vals
                            )
                    for order in orders:
                        order.write({"sale_order_id": sale_order.id})

                # Process each new_order to confirm sale orders and handle payments
                for new_order in new_orders:
                    sale_order = (
                        request.env["sale.order"]
                        .sudo()
                        .search(
                            [
                                ("id", "=", new_order.sale_order_id),
                            ],
                            limit=1,
                        )
                    )

                    if sale_order:
                        # Confirm the sale order only if it is in the 'draft' state
                        if sale_order.state == "draft":
                            sale_order.action_confirm()
                        else:
                            print(
                                f"Sale Order {sale_order.name} is already confirmed or in a state that does not require confirmation."
                            )

                        if payment_method != "cod":
                            try:
                                journal = (
                                    request.env["account.journal"]
                                    .sudo()
                                    .search([("type", "=", "bank")], limit=1)
                                )
                                payment_method = (
                                    request.env["account.payment.method"]
                                    .sudo()
                                    .search([("code", "=", "electronic")], limit=1)
                                )
                                payment = (
                                    request.env["account.payment"]
                                    .sudo()
                                    .create(
                                        {
                                            "payment_type": "inbound",
                                            "partner_type": "customer",
                                            "partner_id": sale_order.partner_id.id,
                                            "amount": sale_order.amount_total,
                                            "journal_id": journal.id,
                                            "payment_method_id": payment_method.id,
                                            "date": fields.Date.today(),
                                        }
                                    )
                                )
                                # Vendor wise total price here
                                price_breakdown = request.session.get(
                                    "price_breakdown", []
                                )
                                for pb in price_breakdown:
                                    print(pb.get("vendor_id"), pb.get("total_price"))

                                payment.action_post()
                                for line in sale_order.order_line:
                                    line.tax_id = False
                                invoice = sale_order._create_invoices()

                                invoice.invoice_date_due = fields.Date.today()
                                invoice.action_post()

                                if (
                                    invoice.state == "posted"
                                    and payment.state == "posted"
                                ):
                                    invoice.js_assign_outstanding_line(payment.id)
                                else:
                                    print(
                                        "Invoice or payment is not posted. Cannot link payment to invoice."
                                    )

                            except Exception as e:
                                print(f"Exception during payment creation: {e}")
                    else:
                        print(f"No Sale Order Found for new_order: {new_order.id}")

            except Exception as e:
                print(f"Exception occurred: {e}")
                return {
                    "success": False,
                    "message": f"{_('Could not place your order at the moment. Please try again later.')} {e}",
                }
            address = (
                request.env["res.partner"]
                .sudo()
                .get_default_address(
                    "billing", new_orders[0].user.commercial_partner_id.id
                )
            )
            email_template = request.env["ir.ui.view"]._render_template(
                "base_accounting_kit.order_placed_email",
                {"my_order": new_orders[0], "address": address},
            )
            mail_response = SendMail
            mail_response.send_email(
                address.email, _("Order being processed"), email_template
            )

            host_url = request.httprequest.host_url
            decoded_url = url_parse(
                f"{host_url}my-orders/order-success={new_orders[0].order_common_token}"
            )
            success_url = decoded_url.to_url()

            return {
                "success": True,
                "success_url": success_url,
                "message": _("The order has been placed successfully."),
            }

        except Exception as e:
            print(f"Outer Exception occurred: {e}")
            return {"success": False, "message": e}

    @http.route(
        "/bad-request",
        type="http",
        # auth="user",
        website=True,
        csrf=False,
    )
    def bad_request(self, **data):
        uid = data.get("spam", False)
        try:
            if uid and not self.is_valid_uuid(uid):
                return request.redirect(f"/not-found?{str(uuid.uuid4())}")
            if not uid or not request.session.get("redirect_url"):
                raise NotFound
            redirect_url = request.session.get("redirect_url", "/")
            return request.render(
                "base_accounting_kit.bad_request", {"redirect_url": redirect_url}
            )
        except NotFound:
            return request.redirect(f"/not-found?{str(uuid.uuid4())}")

    @http.route(
        "/not-found",
        type="http",
        # auth="user",
        website=True,
        csrf=False,
    )
    def not_found(self):

        redirect_url = request.session.get("redirect_url", "/")
        return request.render(
            "base_accounting_kit.not_found", {"redirect_url": redirect_url}
        )

    @http.route(
        "/my-orders",
        type="http",
        auth="user",
        website=True,
        csrf=False,
    )
    def my_orders(self):
        # try:
        options = {}
        orders = (
            request.env["ecommerce.orders"].sudo().get_my_orders(request.env.user.id)
        )

        main_content = request.env["ir.ui.view"]._render_template(
            "base_accounting_kit.my_orders_template",
            {
                "orders": orders,
            },
        )
        options["page_title"] = _("My Dashboard")
        return request.render(
            "base_accounting_kit.dashboard_layout",
            {
                "options": options,
                "main_content": main_content,
            },
        )

    # except Exception as e:
    #     print('error',e)
    # return redirect('/unexpected-event')

    # My orders filter
    @http.route(
        ["/filter_my_order/<string:filter_type>"], type="json", csrf=False, auth="user"
    )
    def filter_my_order(self, filter_type="all", **kwargs):
        try:
            orders = (
                request.env["ecommerce.orders"]
                .sudo()
                .get_my_orders(request.env.user.id, str(filter_type))
            )

            main_content = request.env["ir.ui.view"]._render_template(
                "base_accounting_kit.product_list_adapter",
                {
                    "my_orders": orders,
                },
            )
            return {"success": True, "content": main_content}
        except Exception as e:
            return {"success": False, "message": e}

    @http.route(["/smash_that_order"], type="json", csrf=False, auth="user")
    def smash_that_order(self, **kwargs):
        smash_id = kwargs.get("smash_id", None)
        if not smash_id:
            return {
                "success": False,
                "message": _(
                    "What do you think are you doing? You forgot to pass the smash id duh!!"
                ),
            }
        try:
            order = (
                request.env["ecommerce.orders"]
                .sudo()
                .search([("user", "=", request.env.user.id), ("id", "=", smash_id)])
            )
            if not order:
                return {
                    "success": False,
                    "message": _("Man again? Do not mess up with the system!!"),
                }
            order.write(
                {
                    "status": "abandoned",
                }
            )

            return {"success": True}
        except Exception as e:
            return {"success": False, "message": e}

    @http.route(["/cancel_order"], type="json", csrf=False, auth="user")
    def cancel_that_order(self, **kwargs):
        order_id = kwargs.get("order_id", None)
        if not order_id:
            return {
                "success": False,
                "message": _(
                    "What do you think are you doing? You forgot to pass the order id duh!!"
                ),
            }
        try:
            order = (
                request.env["ecommerce.orders"]
                .sudo()
                .search([("user", "=", request.env.user.id), ("id", "=", order_id)])
            )
            if not order:
                return {
                    "success": False,
                    "message": _("Man again? Do not mess up with the system!!"),
                }
            order.write(
                {
                    "status": "cancelled",
                }
            )

            return {"success": True}
        except Exception as e:
            return {"success": False, "message": e}

    @http.route(["/my-wishlist"], type="json", csrf=False, auth="user")
    def my_wishlist_dynamic_rendering(self, **kwargs):
        my_wishlist = (
            request.env["ecommerce.wishlist"]
            .sudo()
            .get_wishlist_record(user_id=request.env.user.id)
        )
        related_companies = (
            request.env["ecommerce.wishlist"]
            .sudo()
            .get_related_companies(user_id=request.env.user.id)
        )

        template_wishlist = request.env["ir.ui.view"]._render_template(
            "base_accounting_kit.my_wishlist1",
            {"my_wishlist": my_wishlist, "related_companies": related_companies},
        )
        template_main = request.env["ir.ui.view"]._render_template(
            "base_accounting_kit.dashboard_main_content",
            {"page_title": _("My Wishlist"), "main_content": template_wishlist},
        )
        return {"success": True, "data": template_main}

    def is_valid_uuid(self, token):
        try:
            uuid_obj = uuid.UUID(token)
            return str(uuid_obj) == token
        except ValueError:
            return False

    @http.route(["/user_login"], type="json", csrf=False, auth="public")
    def user_login(self, **kwargs):
        try:
            print("gdgdgdg", kwargs)
            login = kwargs.get("email", False)
            password = kwargs.get("password", False)
            if not login or not password:
                return {
                    "success": False,
                    "message": _("Email or password is not supplied!"),
                }
            uid = request.session.authenticate(request.db, login, password)
            if uid:
                return {"success": True, "message": "Login successful", "uid": uid}
            else:
                return {
                    "success": False,
                    "message": _(
                        "No user with given email and password exists in our system."
                    ),
                }

        except Exception as e:
            return {"success": False, "message": str(e)}

    @http.route(
        ["/get_product_attributes_extra_info"], type="json", csrf=False, auth="public"
    )
    def get_product_attributes_extra_info(self, vendor_product_id=None, **data):

        try:
            get_product_attributes = data.get("product_attributes", [])
            attribute_value_pairs = [
                (int(attr.split("-")[0]), int(attr.split("-")[1]))
                for attr in get_product_attributes
            ]

            if not vendor_product_id:
                return {
                    "success": False,
                    "message": _("Bad Request!!"),
                }

            vendor_product = (
                request.env["product.custom.price"]
                .sudo()
                .browse(int(vendor_product_id))
            )
            base_price = vendor_product.price_sell

            if not vendor_product:
                return {
                    "success": False,
                    "message": _("No product with related id found in the system."),
                }

            product_attributes = (
                vendor_product.product_attributes_ids.product_template_value_ids
            )
            attr_price = 0
            for attribute_id, value_id in attribute_value_pairs:
                _product_attributes = product_attributes.search(
                    [
                        ("product_tmpl_id", "=", vendor_product_id),
                        (
                            "product_attribute_value_id.attribute_id.id",
                            "=",
                            attribute_id,
                        ),
                        ("product_attribute_value_id.id", "=", value_id),
                    ]
                )
                attr_price += _product_attributes.price_extra

            product_total_price = base_price + attr_price
            return {"success": True, "product_total_price": product_total_price}

        except Exception as e:
            print("errororor", e)
            return {
                "success": False,
                "message": _("Something went wrong please try again later."),
            }
