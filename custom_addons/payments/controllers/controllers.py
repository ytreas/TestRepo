from odoo import http
from odoo.http import request
import uuid
import requests
from datetime import datetime
import json
import re
import nepali_datetime
from werkzeug.utils import redirect


class OrganizationPaymentsTitles(http.Controller):
    @http.route("/payment-details", auth="user", website=True)
    def get_payments_details(self):
        payment_details = (
            request.env["organization.payment.master"]
            .sudo()
            .search(
                [
                    ("client_id", "=", request.env.user.id),
                    ("payment_status", "=", False),
                ],
                limit=1,
            )
        )
        if payment_details.organization_type == "organization":
            organization_type = "organization.information"
        elif payment_details.organization_type == "tole_bikash":
            organization_type = "tole.bikash.info"
        elif payment_details.organization_type == "upabhokta_samiti":
            organization_type = "upabhokta.samiti.info"
        else:
            organization_type = "organization.basic.information"

        organization = (
            request.env[organization_type]
            .sudo()
            .search([("id", "=", payment_details.organization_id)])
        )
        session_data = request.session.pop("alert_data", {})

        alert_data = {
            "title": session_data.get("title", False),
            "icon": session_data.get("icon", False),
            "message": session_data.get("message", False),
        }
        if payment_details:
            payment_title_amount = payment_details.remarks.split(", ")
            payment_titles = []
            payment_amount = []
            for rec in payment_title_amount:
                    parts = rec.split(" - ")
                    if len(parts) > 1:
                        payment_titles.append(parts[0])
                        payment_amount.append(parts[1])
                    else:
                        alert_data = {
                            "title": "भुक्तानीको लागि कुनै पनि दर भेटिएन। (भुक्तानी योग्य रकम भेटिएन)",
                            "icon": "warning",
                            "message": "भुक्तानीको लागि कुनैपनि दर भेटिएन।",
                        }
                        request.session["alert_data"] = alert_data

            payment_details_rec = {
                "payment_titles": payment_titles,
                "amount_total": payment_details.amount,
                "organization_details": organization,
                "token": payment_details.token,
            }

            unique_id = str(uuid.uuid4().int)
            transaction_id = f"{'BBK'}-{unique_id}"
            return request.render(
                "organization_payments.organization_payment_redirect",
                {
                    "payment_details_rec": payment_details_rec,
                    "payment_amount": payment_amount,
                    "organization": organization,
                    "transaction_id": transaction_id,
                    "alert_data": alert_data,
                },
            )
        else:
            return request.redirect("/")


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
        payment_details = (
            request.env["organization.payment.master"]
            .sudo()
            .search(
                [
                    ("client_id", "=", request.env.user.id),
                    ("payment_status", "=", False),
                ],
                limit=1,
            )
        )

        url = "https://uat.esewa.com.np/epay/transrec"
        payment_gateway = (
            request.env["organization.payment.gateways"]
            .sudo()
            .search([("code", "=", "esewa")], limit=1)
        )
        key = payment_gateway.merchant_api_key
        d = {
            "amt": payment_details.amount,
            "scd": key,
            "rid": data.get("refId"),
            "pid": data.get("oid"),
        }
        resp = requests.post(url, d)
        if resp.status_code == 200:
            gateway_id = (
                request.env["organization.payment.gateways"]
                .sudo()
                .search([("code", "=", "esewa")], limit=1)
            )
            payment_method_revenue_system = (
                request.env["organization.payment.gateways"]
                .sudo()
                .search([("code", "=", "revenue")])
            )

            try:
                payment_details.sudo().write(
                    {
                        "payment_method": gateway_id.id,
                        "transaction_date": nepali_datetime.date.today(),
                        "transaction_id": data.get("oid"),
                        "payment_status": True,
                    }
                )

                revenue_url = payment_method_revenue_system.merchant_api
                revenue_payload = json.dumps(
                    {
                        "ward_wise_psp_mode": False,
                        "ward_no": request.env.user.company_id.id,
                        "counter_code": "044",
                        "payment_method_code": "epay",
                        "name": "संघ संस्था तथा घ वर्ग दर्ता प्रबिधि",
                        "total_amount": payment_details.amount,
                        "external_receipt_number": payment_details.token,  # unique token
                        "remarks": payment_details.remarks,
                        "rate_detail": [
                            {
                                "rate_code": "234",
                                "amount": payment_details.amount,
                                "quantity": 1,
                                "rate_per_unit": payment_details.amount,
                            }
                        ],
                    }
                )
                revenue_headers = {
                    "api_auto_auth": "true",
                    "Authorization": payment_method_revenue_system.merchant_api_key,
                    "Content-Type": "application/json",
                    "Cookie": "app1.acc.munerp=gupuu04wzbdbuqt25kwojt4v",
                }
                revenue_response = requests.request(
                    "POST", revenue_url, headers=revenue_headers, data=revenue_payload
                )
                resp_text = revenue_response.text
                response_dict = json.loads(resp_text)
                print("================================")
                print("================================")
                print(f"================={response_dict}===============")
                print("================================")
                print("================================")
                if revenue_response.status_code == 200:
                    alert_data = {
                        "title": "सफलतापुर्वक भुक्तानी गरियो। धन्यबाद !",
                        "icon": "success",
                        "message": "सफलतापुर्वक भुक्तानी गरियो। धन्यबाद !",
                    }
                else:
                    alert_data = {
                        "title": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                        "icon": "error",
                        "message": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                    }
            except Exception as e:
                alert_data = {
                    "title": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                    "icon": "error",
                    "message": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                }

        else:
            alert_data = {
                "title": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                "icon": "error",
                "message": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
            }
        request.session["alert_data"] = alert_data
        return request.redirect("/payment-details")

    @http.route(
        "/payment-failure",
        type="http",
        auth="user",
        # methods=["POST"],
        csrf=False,
        save_session=True,
    )
    def esewa_payment_failure(self, **data):

        alert_data = {
            "title": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
            "icon": "error",
            "message": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
        }
        request.session["alert_data"] = alert_data
        return request.redirect("/payment-details")

    @http.route(
        "/khalti-initiate",
        type="http",
        auth="user",
        # methods=["POST"],
        csrf=False,
        save_session=True,
    )
    def initiate_khalti(self, **data):
        payment_gateway = (
            request.env["organization.payment.gateways"]
            .sudo()
            .search([("code", "=", "khalti")], limit=1)
        )
        url = payment_gateway.merchant_api
        key = payment_gateway.merchant_api_key
        base_url = request.httprequest.host_url
        payment_details = (
            request.env["organization.payment.master"]
            .sudo()
            .search(
                [
                    ("client_id", "=", request.env.user.id),
                    ("payment_status", "=", False),
                ],
                limit=1,
            )
        )
        payload = json.dumps(
            {
                "return_url": base_url + "khalti-verify/",
                "website_url": base_url,
                "amount": payment_details.amount,
                "purchase_order_id": payment_details.token,
                "purchase_order_name": payment_details.token,
                "customer_info": {
                    "name": request.env.user.name,
                    "email": request.env.user.login,
                    "phone": request.env.user.phone,
                },
            }
        )

        headers = {
            "Authorization": f"key {key}",
            "Content-Type": "application/json",
        }

        response = requests.request("POST", url, headers=headers, data=payload)
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
            return request.redirect("/payment-details")

    @http.route(
        "/khalti-verify",
        type="http",
        auth="user",
        # methods=["POST"],
        csrf=False,
        save_session=True,
    )
    def verify_khalti(self, **data):
        payment_gateway = (
            request.env["organization.payment.gateways"]
            .sudo()
            .search([("code", "=", "khalti")], limit=1)
        )
        payment_details = (
            request.env["organization.payment.master"]
            .sudo()
            .search(
                [
                    ("client_id", "=", request.env.user.id),
                    ("payment_status", "=", False),
                ],
                limit=1,
            )
        )
        url = "https://a.khalti.com/api/v2/epayment/lookup/"
        payment_gateway = (
            request.env["organization.payment.gateways"]
            .sudo()
            .search([("code", "=", "khalti")], limit=1)
        )
        if request.httprequest.method == "GET":
            pidx = data.get("pidx")
            payload = json.dumps({"pidx": pidx})
            headers = {
                "Authorization": f"key {payment_gateway.merchant_api_key}",
                "Content-Type": "application/json",
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 200:
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

                        payment_method_revenue_system = (
                            request.env["organization.payment.gateways"]
                            .sudo()
                            .search([("code", "=", "revenue")])
                        )
                        revenue_url = payment_method_revenue_system.merchant_api
                        revenue_payload = json.dumps(
                            {
                                "ward_wise_psp_mode": False,
                                "ward_no": request.env.user.company_id.id,
                                "counter_code": "044",
                                "payment_method_code": "epay",
                                "name": "संघ संस्था तथा घ वर्ग दर्ता प्रबिधि",
                                "total_amount": payment_details.amount,
                                "external_receipt_number": payment_details.token,  # unique token
                                "remarks": payment_details.remarks,
                                "rate_detail": [
                                    {
                                        "rate_code": "234",
                                        "amount": payment_details.amount,
                                        "quantity": 1,
                                        "rate_per_unit": payment_details.amount,
                                    }
                                ],
                            }
                        )
                        revenue_headers = {
                            "api_auto_auth": "true",
                            "Authorization": payment_method_revenue_system.merchant_api_key,
                            "Content-Type": "application/json",
                            "Cookie": "app1.acc.munerp=gupuu04wzbdbuqt25kwojt4v",
                        }
                        revenue_response = requests.request(
                            "POST",
                            revenue_url,
                            headers=revenue_headers,
                            data=revenue_payload,
                        )
                        resp_text = revenue_response.text
                        response_dict = json.loads(resp_text)
                        if revenue_response.status_code == 200:
                            alert_data = {
                                "title": "सफलतापुर्वक भुक्तानी गरियो। धन्यबाद !",
                                "icon": "success",
                                "message": "सफलतापुर्वक भुक्तानी गरियो। धन्यबाद !",
                            }
                        else:
                            alert_data = {
                                "title": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                                "icon": "error",
                                "message": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                            }
                        alert_data = {
                            "title": "सफलतापुर्वक भुक्तानी गरियो। धन्यबाद !",
                            "icon": "success",
                            "message": "सफलतापुर्वक भुक्तानी गरियो। धन्यबाद !",
                        }
                    except Exception as e:
                        alert_data = {
                            "title": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                            "icon": "error",
                            "message": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                        }
                    request.session["alert_data"] = alert_data
                    return request.redirect("/payment-details")
            else:
                alert_data = {
                    "title": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                    "icon": "error",
                    "message": "भुक्तानी संम्पन्न हुन सकेन। धन्यबाद !",
                }
                request.session["alert_data"] = alert_data
                return request.redirect("/payment-details")
