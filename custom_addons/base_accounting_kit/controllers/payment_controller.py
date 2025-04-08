from odoo import http, _
from odoo.http import request
import uuid
import requests
from datetime import datetime
import json
import re
import nepali_datetime
from werkzeug.utils import redirect
import hmac
import hashlib
import base64
from odoo.exceptions import ValidationError
import os
from dotenv import load_dotenv

load_dotenv()
ESEWA_PRODUCT_KEY = os.getenv("ESEWA_PRODUCT_KEY", "EPAYTEST")
ESEWA_CLIENT_KEY = os.getenv("ESEWA_CLIENT_KEY", "8gBm/:&EnhH.1/q")
STATUS_TEST_URL = "https://epay.esewa.com.np/api/epay/transaction/status/"


class PaymentGatewayController(http.Controller):
    @http.route(
        "/payment-success",
        type="http",
        auth="user",
        # methods=["POST"],
        csrf=False,
        save_session=True,
    )
    def esewa_payment_success(self, **data):

        base64_encoded_str = data.get("data")
        decoded_bytes = base64.b64decode(base64_encoded_str)
        decoded_str = decoded_bytes.decode("utf-8")
        decoded_data = json.loads(decoded_str)

        transaction_uuid = decoded_data.get("transaction_uuid")
        payment_details = (
            request.env["lekhaplus.payment.master"]
            .sudo()
            .search(
                [
                    ("client_id", "=", request.env.user.id),
                    ("transaction_id", "=", transaction_uuid),
                    ("payment_status", "=", False),
                ],
                limit=1,
            )
        )

        url = STATUS_TEST_URL

        d = {
            "product_code": ESEWA_PRODUCT_KEY,
            "transaction_uuid": decoded_data.get("transaction_uuid"),
            "total_amount": decoded_data.get("total_amount"),
        }
        try:
            resp = requests.get(url, params=d)
            base_url = request.httprequest.host_url
            json_resp_data = resp.json()
            resp.raise_for_status()
        except Exception as e:
            print(f"Error during the request to eSewa: {e}")
            return request.redirect(f"{base_url}payment-failure")

        if resp.status_code == 200 and json_resp_data.get("status") == "COMPLETE":
            return_url = (
                f"{base_url}payment-successful/{payment_details.transaction_id}"
            )
            payment_details.sudo().write({"payment_success_from_provider": True})

            gateway_id = (
                request.env["custom.payment.gateways"]
                .sudo()
                .search(
                    [
                        ("payment_method_name", "=", "esewa"),
                        ("company_id", "=", request.env.user.company_id.id),
                    ],
                    limit=1,
                )
            )
            try:
                payment_details.sudo().write(
                    {
                        "payment_method": gateway_id.id,
                        "transaction_date": nepali_datetime.date.today(),
                        "transaction_id": decoded_data.get("transaction_uuid"),
                        "payment_status": True,
                    }
                )

                account_move_id = (
                    request.env["account.move"]
                    .sudo()
                    .search([("id", "=", payment_details.account_move_id)])
                )

                account_move_id.write(
                    {
                        "payment_state": "paid",
                        "invoice_user_id": request.env.user.id,
                        "amount_residual_signed": 0,
                    }
                )

                return redirect(return_url)
            except Exception as e:
                request.session["error_message"] = (
                    f"{_('Your payment is done but could not registered in the system due to -')}[{e}]. {_('Please contact your admin for registering your payment in the system.')}",
                )

        else:
            return_url = f"{base_url}payment-failure"

            request.session["error_message"] = _("Payment Unsuccessful")
            return request.redirect(return_url)

    @http.route(
        "/payment-failure",
        type="http",
        auth="user",
        # methods=["POST"],
        csrf=False,
        save_session=True,
    )
    def esewa_payment_failure(self, **data):
        base_url = request.httprequest.host_url
        return_url = f"{base_url}lekha-payment-failure"
        alert_data = {
            "title": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
            "icon": "error",
            "message": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
        }
        request.session["alert_data"] = alert_data
        return request.redirect(return_url)

    @http.route(
        "/khalti-initiate",
        type="http",
        auth="user",
        csrf=False,
        save_session=True,
    )
    def initiate_khalti(self, **data):
        session_data = request.session.pop("khalti_data", {})
        session_data.get("amount", False),

        payment_gateway = (
            request.env["custom.payment.gateways"]
            .sudo()
            .search(
                [
                    ("payment_method_name", "=", "khalti"),
                    ("company_id", "=", request.env.user.company_id.id),
                ],
                limit=1,
            )
        )
        url = payment_gateway.merchant_api
        key = payment_gateway.merchant_api_key
        base_url = request.httprequest.host_url

        payload = json.dumps(
            {
                "return_url": base_url + "khalti-verify/",
                "website_url": base_url,
                "amount": int(session_data.get("amount")),
                "purchase_order_id": session_data.get("transaction_id"),
                "purchase_order_name": "payment_details.token",
                "customer_info": {
                    "name": request.env.user.name,
                    "email": "kumarbibek094@gmail.com",
                    "phone": "9810040057",
                },
            }
        )

        headers = {
            "Authorization": f"key {key}",
            "Content-Type": "application/json",
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        print("response")
        print(response.text)
        if response.status_code == 200:
            resp_text = response.text
            response_dict = json.loads(resp_text)
            payment_url = response_dict["payment_url"]

            return redirect(f"{payment_url}")
        else:
            alert_data = {
                "title": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                "icon": "error",
                "message": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
            }
            request.session["alert_data"] = alert_data
            return request.redirect("/lekha-payment-failure")

    @http.route(
        "/khalti-verify",
        type="http",
        auth="user",
        # methods=["POST"],
        csrf=False,
        save_session=True,
    )
    def verify_khalti(self, **data):

        if request.httprequest.method == "GET":
            payment_gateway = (
                request.env["custom.payment.gateways"]
                .sudo()
                .search(
                    [
                        ("payment_method_name", "=", "khalti"),
                        ("company_id", "=", request.env.user.company_id.id),
                    ],
                    limit=1,
                )
            )

            url = "https://a.khalti.com/api/v2/epayment/lookup/"
            pidx = data.get("pidx")
            payment_details = (
                request.env["lekhaplus.payment.master"]
                .sudo()
                .search(
                    [
                        ("client_id", "=", request.env.user.id),
                        ("transaction_id", "=", pidx),
                        ("payment_status", "=", False),
                    ],
                    limit=1,
                )
            )
            payload = json.dumps({"pidx": pidx})
            headers = {
                "Authorization": f"key {payment_gateway.merchant_api_key}",
                "Content-Type": "application/json",
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            base_url = request.httprequest.host_url
            return_url = (
                f"{base_url}payment-successful/{payment_details.transaction_id}"
            )
            if response.status_code == 200:
                request.session["success_message"] = _("Payment successful")
                payment_details.sudo().write({"payment_success_from_provider": True})

                resp_text = response.text
                response_dict = json.loads(resp_text)
                if response_dict["status"] == "Completed":
                    try:
                        payment_details.sudo().write(
                            {
                                "payment_method": payment_gateway.id,
                                "transaction_date": nepali_datetime.date.today(),
                                "transaction_id": response_dict["transaction_id"],
                                "payment_status": True,
                            }
                        )

                        account_move_id = (
                            request.env["account.move"]
                            .sudo()
                            .search([("id", "=", payment_details.account_move_id)])
                        )
                        account_move_id.write(
                            {
                                "payment_state": "paid",
                                "invoice_user_id": request.env.user.id,
                                "amount_residual_signed": 0,
                            }
                        )

                        return redirect(return_url)
                    except Exception as e:
                        request.session["error_message"] = _("Payment Unsuccessful")
                        return request.redirect(return_url)
            else:
                request.session["error_message"] = _("Payment Unsuccessful")
                return request.redirect(return_url)

    @http.route(
        "/redirect-esewa",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def redirect_esewa(self, **data):
        session_data = request.session.pop("esewa_data", {})
        amt = session_data.get("amt", False)
        pid = session_data.get("pid", False)
        tAmt = session_data.get("tAmt", False)
        txAmt = session_data.get("txAmt", False)
        scd = session_data.get("scd", False)
        base_url = request.httprequest.host_url
        payment_gateway = (
            request.env["custom.payment.gateways"]
            .sudo()
            .search(
                [
                    ("payment_method_name", "=", "esewa"),
                    ("company_id", "=", request.env.user.company_id.id),
                ],
                limit=1,
            )
        )
        message = f"total_amount={tAmt},transaction_uuid={pid},product_code={ESEWA_PRODUCT_KEY}"
        secret = ESEWA_CLIENT_KEY

        hash_bytes = hmac.new(
            secret.encode(), message.encode(), hashlib.sha256
        ).digest()

        hash_in_base64 = base64.b64encode(hash_bytes).decode()

        print("signature")
        print(hash_in_base64)
        payment_details = {
            "amt": amt,
            "pid": pid,
            "tAmt": tAmt,
            "txAmt": txAmt,
            "scd": ESEWA_PRODUCT_KEY,
            "signature": ESEWA_CLIENT_KEY,
            "su": f"{base_url}/payment-success",
            "fu": f"{base_url}/payment-failure",
            "hash_in_base64": hash_in_base64,
        }

        request.session["esewa_validation_data"] = {
            "uid": request.env.user.id,
            "transaction_id": pid,
        }

        print(payment_details)
        return request.render(
            "base_accounting_kit.payment_redirect_template",
            {"payment_details": payment_details},
        )

    @http.route(
        "/payment/bill/<string:access_token>",
        type="http",
        methods=["GET"],
        csrf=False,
    )
    def portal_bill_payment(self, access_token, **data):

        bill_no = (
            request.env["account.move"]
            .sudo()
            .search([("access_token", "=", access_token)], limit=1)
        )
        if not bill_no:
            return redirect("/invalid")
        transaction_id = str(uuid.uuid4().int)
        amt = bill_no.amount_residual
        invoice_line_command = [(6, 0, bill_no.invoice_line_ids.ids)]
        rem = ""
        if (
            invoice_line_command
            and isinstance(invoice_line_command, list)
            and invoice_line_command[0][0] == 6
        ):
            invoice_line_ids = invoice_line_command[0][2]
            invoice_lines = request.env["account.move.line"].browse(invoice_line_ids)
            if invoice_lines:
                for inv in invoice_lines:
                    rem += f"{inv.name}, \n"
        try:
            bill_payment_master = (
                request.env["lekhaplus.payment.master"]
                .sudo()
                .create(
                    {
                        "amount": amt,
                        "account_move_id": bill_no.id,
                        "transaction_id": transaction_id,
                        "remarks": rem,
                        "client_id": bill_no.partner_id.id,
                        "tax_amount": bill_no.amount_tax,
                    }
                )
            )
        except Exception as e:
            raise ValidationError(
                f"{_('Unable to proceed for the payment due to- ')}[{e}]"
            )

        base_url = request.httprequest.host_url
        payment_gateway = (
            request.env["custom.payment.gateways"]
            .sudo()
            .search(
                [
                    ("payment_method_name", "=", "esewa"),
                    ("company_id", "=", request.env.user.company_id.id),
                ],
                limit=1,
            )
        )
        message = f"total_amount={amt},transaction_uuid={transaction_id},product_code={ESEWA_PRODUCT_KEY}"
        secret = ESEWA_CLIENT_KEY

        hash_bytes = hmac.new(
            secret.encode(), message.encode(), hashlib.sha256
        ).digest()

        hash_in_base64 = base64.b64encode(hash_bytes).decode()

        payment_details = {
            "amt": amt,
            "pid": transaction_id,
            "tAmt": amt,
            "txAmt": amt,
            "scd": ESEWA_PRODUCT_KEY,
            "signature": ESEWA_CLIENT_KEY,
            "su": f"{base_url}/payment-success",
            "fu": f"{base_url}/payment-failure",
            "hash_in_base64": hash_in_base64,
        }

        request.session["esewa_validation_data"] = {
            "uid": request.env.user.id,
            "transaction_id": transaction_id,
        }

        return request.render(
            "base_accounting_kit.payment_redirect_template",
            {"payment_details": payment_details},
        )

    @http.route(
        "/payment-successful/<int:transaction_id>",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def payment_successful(self, transaction_id, **data):
        try:
            payment_master = (
                request.env["lekhaplus.payment.master"]
                .sudo()
                .search(
                    [
                        ("transaction_id", "=", transaction_id),
                        ("payment_status", "=", True),
                        ("company_id", "=", request.env.user.company_id.id),
                    ],
                    limit=1,
                )
            )
            if not payment_master:
                return request.redirect("/invalid")

            base_url = request.httprequest.host_url
            action_data = (
                request.env["ir.actions.act_window"]
                .sudo()
                .search([("res_model", "=", "account.move")], limit=1)
            )

            redirect_url = f"{base_url}web#id={payment_master.account_move_id}&action={action_data.id}&model=account.move&view_type=form"

            return request.render(
                "base_accounting_kit.payment_successful", {"redirect_url": redirect_url}
            )

        except Exception as e:
            raise ValidationError(
                f'{_("Unexpected error ocurred, please navigate to the invoice bill manually. We are sorry for the inconvenience!")}- [{e}]'
            )

    @http.route(
        "/lekha-payment-failure",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def lekha_payment_failure(self, **data):
        return request.render(
            "base_accounting_kit.payment_failure",
        )

    @http.route(
        "/client-payment-success",
        type="http",
        auth="public",
        # methods=["POST"],
        csrf=False,
        save_session=True,
    )
    def esewa_client_payment_success(self, **data):

        base64_encoded_str = data.get("data")
        decoded_bytes = base64.b64decode(base64_encoded_str)
        decoded_str = decoded_bytes.decode("utf-8")
        decoded_data = json.loads(decoded_str)

        transaction_uuid = decoded_data.get("transaction_uuid")

        payment_details = (
            request.env["lekhaplus.service.payment"]
            .sudo()
            .search(
                [
                    ("transaction_id", "=", transaction_uuid),
                    ("payment_status", "=", False),
                ],
                limit=1,
            )
        )

        url = STATUS_TEST_URL

        d = {
            "product_code": ESEWA_PRODUCT_KEY,
            "transaction_uuid": decoded_data.get("transaction_uuid"),
            "total_amount": decoded_data.get("total_amount"),
        }
        try:
            resp = requests.get(url, params=d)
            base_url = request.httprequest.host_url
            json_resp_data = resp.json()
            print("json_resp_data")
            print(json_resp_data)
            resp.raise_for_status()
        except Exception as e:
            print(f"Error during the request to eSewa: {e}")
            return request.redirect(f"{base_url}payment-failure")

        if resp.status_code == 200 and json_resp_data.get("status") == "COMPLETE":
            return_url = (
                f"{base_url}client-payment-successful/{payment_details.transaction_id}"
            )
            payment_details.sudo().write({"payment_provider_status": True})

            try:
                payment_details.sudo().write(
                    {
                        # "transaction_date": nepali_datetime.date.today(),
                        "subscription_status": True,
                        "payment_status": True,
                    }
                )
                return redirect(return_url)
            except Exception as e:
                request.session["error_message"] = (
                    f"{_('Your payment is done but could not registered in the system due to -')}[{e}]. {_('Please contact your admin for registering your payment in the system.')}",
                )

        else:
            return_url = f"{base_url}payment-failure"

            request.session["error_message"] = _("Payment Unsuccessful")
            return request.redirect(return_url)

    @http.route(
        "/client-payment-failure",
        type="http",
        auth="public",
        # methods=["POST"],
        csrf=False,
        save_session=True,
    )
    def esewa_client_payment_failure(self, **data):
        base_url = request.httprequest.host_url
        return_url = f"{base_url}lekha-payment-failure"
        return request.redirect(return_url)

    @http.route(
        "/get-payment-status/<string:email>",
        type="http",
        methods=["GET"],
        auth="public",
        csrf=False,
        save_session=True,
    )
    def get_payment_status(self, email, **data):

        payment_master = (
            request.env["lekhaplus.service.payment"]
            .sudo()
            .search(
                [
                    ("client", "=", email),
                    ("payment_status", "=", True),
                    ("subscription_status", "=", True),
                ]
            )
        )

        if payment_master:
            return request.make_response(
                json.dumps(
                    {
                        "success": True,
                        "client": payment_master.client,
                    }
                ),
                status=200,
                headers=[("Content-Type", "application/json")],
            )

    @http.route(
        "/registration/proceed-to-payment",
        type="http",
        methods=["POST"],
        auth="public",
        csrf=False,
        save_session=True,
    )
    def registration_proceed_to_payment(self, **data):
        base_url = request.httprequest.host_url
        tAmt = data.get("amount")
        email = data.get("email")
        pid = str(uuid.uuid4().int)
        service_type = data.get("business_ids")
        service_type_ids = (
            [int(x) for x in service_type.split(",") if x.isdigit()]
            if service_type
            else []
        )
        service_type_ids = [x for x in service_type_ids if isinstance(x, int) and x > 0]
        try:
            if not tAmt or not email:
                return request.redirect(request.httprequest.referrer)
            service_payment_master_rec = (
                request.env["lekhaplus.service.payment"]
                .sudo()
                .search([("client", "=", email)])
            )

            if not service_payment_master_rec:
                service_payment_master = (
                    request.env["lekhaplus.service.payment"]
                    .sudo()
                    .create(
                        {
                            "transaction_id": pid,
                            "client": email,
                            "amount": float(tAmt),
                            "service_type": [(6, 0, service_type_ids)],
                        }
                    )
                )

            service_payment_master_rec.write(
                {
                    "transaction_id": pid,
                    "client": email,
                    "amount": float(tAmt),
                    "service_type": [(6, 0, service_type)],
                }
            )
            message = f"total_amount={tAmt},transaction_uuid={pid},product_code={ESEWA_PRODUCT_KEY}"
            secret = ESEWA_CLIENT_KEY

            hash_bytes = hmac.new(
                secret.encode(), message.encode(), hashlib.sha256
            ).digest()

            hash_in_base64 = base64.b64encode(hash_bytes).decode()
            payment_details = {
                "pid": pid,
                "tAmt": tAmt,
                "scd": ESEWA_PRODUCT_KEY,
                "su": f"{base_url}/client-payment-success",
                "fu": f"{base_url}/client-payment-failure",
                "hash_in_base64": hash_in_base64,
            }

            return request.render(
                "base_accounting_kit.payment_redirect_template",
                {"payment_details": payment_details},
            )
        except Exception as e:
            return request.render(
                "base_accounting_kit.web_system_client_error",
                {"error": e},
            )

    @http.route(
        "/client-payment-successful/<int:transaction_id>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def client_payment_successful(self, transaction_id, **data):
        try:
            payment_master = (
                request.env["lekhaplus.service.payment"]
                .sudo()
                .search(
                    [
                        ("transaction_id", "=", transaction_id),
                        ("payment_status", "=", True),
                    ],
                    limit=1,
                )
            )
            if not payment_master:
                return request.redirect("/invalid")

            base_url = request.httprequest.host_url

            return request.render("base_accounting_kit.client_payment_successful")

        except Exception as e:
            raise ValidationError(
                f'{_("Unexpected error ocurred, please navigate to the invoice bill manually. We are sorry for the inconvenience!")}- [{e}]'
            )


# API
from . import jwt_token_auth

API_SECRET_KEY = os.getenv("API_SECRET_KEY")


class PaymentAPI(http.Controller):

    # Bills payment
    @http.route(
        "/api/v1/bills-payment",
        type="http",
        auth="public",
        cors="*",
        csrf=False,
    )
    def bills_payment(self, **data):
        auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(
            self, request
        )
        if auth_status["status"] == "fail":
            return request.make_response(
                json.dumps(auth_status),
                headers=[("Content-Type", "application/json")],
                status=status_code,
            )
        raw_data = request.httprequest.data
        json_data = json.loads(raw_data)
        transaction_uuid = json_data.get("transaction_uuid")
        client_id = json_data.get("client_id")
        bill_id = json_data.get("bill_id")
        amount_paid = json_data.get("amount_paid")

        if not transaction_uuid or not client_id or not bill_id or not amount_paid:
            return request.make_response(
                json.dumps(
                    {
                        "success": False,
                        "error": _(
                            "Transaction ID, Client ID, Bill ID, and Amount Paid are required."
                        ),
                    }
                ),
                status=400,
                headers=[("Content-Type", "application/json")],
            )

        try:
            payment_details = (
                request.env["lekhaplus.payment.master"]
                .sudo()
                .search(
                    [
                        ("client_id", "=", int(client_id)),
                        ("transaction_id", "=", transaction_uuid),
                        ("payment_status", "=", False),
                    ],
                    limit=1,
                )
            )
            gateway_id = (
                request.env["custom.payment.gateways"]
                .sudo()
                .search(
                    [
                        ("payment_method_name", "=", "esewa"),
                    ],
                    limit=1,
                )
            )
            if not gateway_id:
                return request.make_response(
                    json.dumps(
                        {
                            "success": False,
                            "error": f'{_("Payment Gateway not Registered")}',
                        }
                    ),
                    status=400,
                    headers=[("Content-Type", "application/json")],
                )
            payment_details.write(
                {
                    "payment_method": gateway_id.id,
                    "transaction_date": nepali_datetime.date.today(),
                    "transaction_id": transaction_uuid,
                    "payment_status": True,
                    "payment_success_from_provider": True,
                }
            )
            account_move_id = (
                request.env["account.move"]
                .sudo()
                .search([("id", "=", payment_details.account_move_id)])
            )

            if not account_move_id:
                return request.make_response(
                    json.dumps(
                        {
                            "success": False,
                            "error": f'{_("Bill ID does not exist in the system")}',
                        }
                    ),
                    status=400,
                    headers=[("Content-Type", "application/json")],
                )
            account_move_id.write(
                {
                    "payment_state": "paid",
                    "invoice_user_id": client_id,
                    "amount_residual_signed": 0,
                }
            )

            return request.make_response(
                json.dumps(
                    {
                        "success": True,
                        "error": f'{_("Payment successfully registered in the system")}',
                    }
                ),
                status=200,
                headers=[("Content-Type", "application/json")],
            )

        except Exception as e:
            return request.make_response(
                json.dumps(
                    {
                        "success": False,
                        "error": f'{_("Transaction Failed due to- ")} {e}',
                    }
                ),
                status=500,
                headers=[("Content-Type", "application/json")],
            )

    @http.route(
        "/api/v1/system-failed-payment",
        type="http",
        auth="public",
        cors="*",
        csrf=False,
    )
    def system_failed_payment(self, **data):
        auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(
            self, request
        )
        if auth_status["status"] == "fail":
            return request.make_response(
                json.dumps(auth_status),
                headers=[("Content-Type", "application/json")],
                status=status_code,
            )
        raw_data = request.httprequest.data
        json_data = json.loads(raw_data)
        transaction_uuid = json_data.get("transaction_uuid")
        client_id = json_data.get("client_id")
        bill_id = json_data.get("bill_id")
        amount_paid = json_data.get("amount_paid")

        if not transaction_uuid or not client_id or not bill_id or not amount_paid:
            return request.make_response(
                json.dumps(
                    {
                        "success": False,
                        "error": _(
                            "Transaction ID, Client ID, Bill ID, and Amount Paid are required."
                        ),
                    }
                ),
                status=400,
                headers=[("Content-Type", "application/json")],
            )

        try:
            payment_details = (
                request.env["lekhaplus.payment.master"]
                .sudo()
                .search(
                    [
                        ("client_id", "=", int(client_id)),
                        ("transaction_id", "=", transaction_uuid),
                        ("payment_status", "=", False),
                    ],
                    limit=1,
                )
            )
            gateway_id = (
                request.env["custom.payment.gateways"]
                .sudo()
                .search(
                    [
                        ("payment_method_name", "=", "esewa"),
                    ],
                    limit=1,
                )
            )
            if not gateway_id:
                return request.make_response(
                    json.dumps(
                        {
                            "success": False,
                            "error": f'{_("Payment Gateway not Registered")}',
                        }
                    ),
                    status=400,
                    headers=[("Content-Type", "application/json")],
                )
            payment_details.write(
                {
                    "payment_method": gateway_id.id,
                    "transaction_date": nepali_datetime.date.today(),
                    "transaction_id": transaction_uuid,
                    "payment_status": True,
                    "payment_success_from_provider": True,
                }
            )
            account_move_id = (
                request.env["account.move"]
                .sudo()
                .search([("id", "=", payment_details.account_move_id)])
            )

            if not account_move_id:
                return request.make_response(
                    json.dumps(
                        {
                            "success": False,
                            "error": f'{_("Bill ID does not exist in the system")}',
                        }
                    ),
                    status=400,
                    headers=[("Content-Type", "application/json")],
                )
            account_move_id.write(
                {
                    "payment_state": "paid",
                    "invoice_user_id": client_id,
                    "amount_residual_signed": 0,
                }
            )

            return request.make_response(
                json.dumps(
                    {
                        "success": True,
                        "message": f'{_("Payment successfully registered in the system")}',
                    }
                ),
                status=200,
                headers=[("Content-Type", "application/json")],
            )

        except Exception as e:
            return request.make_response(
                json.dumps(
                    {
                        "success": False,
                        "error": f'{_("Transaction Failed due to- ")} {e}',
                    }
                ),
                status=500,
                headers=[("Content-Type", "application/json")],
            )

    # User registration payment
    @http.route(
        "/api/v1/user-registration-payment",
        type="http",
        auth="public",
        cors="*",
        csrf=False,
    )
    def user_registration_payment(self, **data):
        raw_data = request.httprequest.data
        json_data = json.loads(raw_data)

        transaction_uuid = json_data.get("transaction_uuid")
        client_email = json_data.get("client_email")
        amount = json_data.get("amount")
        service_type = json_data.get("service_type")  # 1,2,3
        service_type_ids = (
            list(map(int, service_type.split(","))) if service_type else []
        )
        if not transaction_uuid or not client_email or not amount or not service_type:
            return request.make_response(
                json.dumps(
                    {
                        "success": False,
                        "error": _(
                            "Transaction id, client email,amount and service types are required."
                        ),
                    }
                ),
                status=400,
                headers=[("Content-Type", "application/json")],
            )

        secret_key = json_data.get("secret_key")

        if not secret_key and not secret_key == API_SECRET_KEY:
            return request.make_response(
                json.dumps(
                    {
                        "success": False,
                        "error": _("API Could not be authenticated."),
                    }
                ),
                status=400,
                headers=[("Content-Type", "application/json")],
            )
        try:
            service_payment_master_rec = (
                request.env["lekhaplus.service.payment"]
                .sudo()
                .search([("client", "=", client_email)])
            )
            if not service_payment_master_rec:
                service_payment_master = (
                    request.env["lekhaplus.service.payment"]
                    .sudo()
                    .create(
                        {
                            "transaction_id": transaction_uuid,
                            "client": client_email,
                            "amount": amount,
                            "service_type": [(6, 0, service_type_ids)],
                        }
                    )
                )
            service_payment_master_rec.write(
                {
                    "transaction_id": transaction_uuid,
                    "client": client_email,
                    "amount": amount,
                    "service_type": [(6, 0, service_type)],
                }
            )
            return request.make_response(
                json.dumps(
                    {
                        "success": True,
                        "message": "The payment is successfully registered in the system",
                    }
                ),
                status=500,
                headers=[("Content-Type", "application/json")],
            )
        except Exception as e:
            return request.make_response(
                json.dumps(
                    {
                        "success": False,
                        "error": f"Unexpected error occurred- {e}",
                    }
                ),
                status=500,
                headers=[("Content-Type", "application/json")],
            )
