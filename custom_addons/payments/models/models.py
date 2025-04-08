from odoo import api, fields, models
from odoo.exceptions import ValidationError
import requests
import json
import datetime
import uuid


class OrganizationPayments(models.Model):
    _name = "organization.payment.titles"
    _rec_name = "name_en"

    code = fields.Char("Code")
    name_en = fields.Char("Name EN")
    name_np = fields.Char("Name NP")
    rate_per_unit = fields.Char("Rate Per Unit")

    def get_payments_titles(self):
        auth_url = "http://kathmandu.acc.shangrilagroup.com.np/api/auth/authenticate"
        auth_data = {
            "client_id": "178",
            "username": "kmcapiuser",
            "password": "pOiUr@58ep",
        }
        auth_response = requests.post(auth_url, json=auth_data)

        if auth_response.ok:
            auth_data = auth_response.json()
            headers = {
                "token": auth_data.get("token"),
                "user_id": str(auth_data.get("user_id")),
            }

            rate_url = "http://kathmandu.acc.shangrilagroup.com.np/api/RevEndServices/EndPort/GetRateInfo"
            rate_data = {"service_receiver_code": "Ij@s3"}
            rate_response = requests.post(rate_url, json=rate_data, headers=headers)
            payment_titles_model = (
                self.env["organization.payment.titles"].sudo().search([])
            )

            if rate_response.ok:
                record_data = rate_response.json().get("data")
                for record in record_data:
                    check_if_exists = (
                        self.env["organization.payment.titles"]
                        .sudo()
                        .search([("code", "=", record["code"])])
                    )
                    if check_if_exists:
                        check_if_exists.write(
                            {
                                "code": record["code"],
                                "name_en": record["name_en"],
                                "name_np": record["name_np"],
                                "rate_per_unit": record["rate_per_unit"],
                            }
                        )
                    else:
                        self.env["organization.payment.titles"].sudo().create(
                            {
                                "code": record["code"],
                                "name_en": record["name_en"],
                                "name_np": record["name_np"],
                                "rate_per_unit": record["rate_per_unit"],
                            }
                        )

            else:
                error_code = rate_response.status_code
                error_message = rate_response.text
        else:
            error_code = auth_response.status_code
            error_message = auth_response.text


class PaymentFromRevenueSystem(models.Model):
    _name = "revenue.system.payment"
    _rec_name = "payment_token"

    payment_token = fields.Many2one(
        "organization.payment.master",
        store=True,
        string="Token",
        domain="[('payment_status', '=', False),('client_id','!=',False)]",
    )
    organization_name = fields.Char()
    organization_id = fields.Integer()
    client_id = fields.Many2one(
        "res.users",
        "Client Name/Email",
        store=True,
        required=True,
    )
    amount = fields.Float("amount", store=True, required=True)
    transaction_date = fields.Char(
        "transaction_date", default=fields.Date.today, store=True
    )
    tax_revenue_receipt_no = fields.Char("tax_revenue_receipt_no", store=True)
    tax_revenue_receipt_url = fields.Char("Receipt link", store=True)
    tax_revenue_receipt_name = fields.Char("Receipt link", store=True)
    remarks = fields.Char(
        "remarks",
        store=True,
        compute="save_payment_attributes",
    )

    

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.payment_token, rec.client_id))
        return result

    @api.onchange("payment_token")
    def set_payment_attributes(self):
        try:
            payment_master = (
                self.env["organization.payment.master"]
                .sudo()
                .search([("token", "=", self.payment_token.token)])
            )
            self.client_id = payment_master.client_id
            self.amount = payment_master.amount
        except Exception as e:
            raise ValidationError('कार्य सम्पन्न हुन सकेन पुन: प्रयास गर्नुहोला। कारण यसप्रकार रहेको छ: ',e)

    @api.depends("payment_token")
    def save_payment_attributes(self):
        try:
            payment_master = (
                self.env["organization.payment.master"]
                .sudo()
                .search([
                        ("token", "=", self.payment_token.token)])
            )
            self.client_id = payment_master.client_id
            self.amount = payment_master.amount
            self.transaction_date = datetime.date.today()
        except Exception as e:
            raise ValidationError('कार्य सम्पन्न हुन सकेन पुन: प्रयास गर्नुहोला। कारण यसप्रकार रहेको छ: ',e)
        
    def proceed_for_payment(self):
        payment_master = (
            self.env["organization.payment.master"]
            .sudo()
            .search([("token", "=", self.payment_token.token)])
        )
        payment_methods = (
            self.env["organization.payment.gateways"]
            .sudo()
            .search([("code", "=", "revenue")])
        )
        url = payment_methods.merchant_api

        payload = json.dumps(
            {
                "ward_wise_psp_mode": False,
                "ward_no": self.env.user.company_id.id,
                "counter_code": "044",
                "name": "संघ संस्था तथा घ वर्ग दर्ता प्रबिधि",
                "total_amount": payment_master.amount,
                "external_receipt_number": payment_master.token,  
                "remarks": payment_master.remarks,
                "rate_detail": [
                    {
                        "rate_code": "234",
                        "amount": payment_master.amount,
                        "quantity": 1,
                        "rate_per_unit": payment_master.amount,
                    }
                ],
            }
        )
        headers = {
            "api_auto_auth": "true",
            "Authorization": payment_methods.merchant_api_key,
            "Content-Type": "application/json",
            "Cookie": "app1.acc.munerp=gupuu04wzbdbuqt25kwojt4v",
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            resp_text = response.text
            response_dict = json.loads(resp_text)
            if response.status_code == 200:
                modal = (
                    self.env["organization.payment.master"]
                    .sudo()
                    .browse(payment_master.id)
                )
                modal.write(
                    {
                        "payment_method": payment_methods.id,
                        "transaction_date": datetime.date.today(),
                        "transaction_id": response_dict["data"]["receipt_no"],
                        "invoice_id": response_dict["data"]["receipt_no"],
                        "tax_revenue_receipt_no": response_dict["data"]["receipt_no"],
                        "payment_status": True,
                    }
                )
                self.tax_revenue_receipt_no = response_dict["data"]["receipt_no"]
                self.transaction_date = datetime.date.today()
                self.remarks = response_dict["message"]
                self.organization_name = modal.organization_name
                self.organization_id = modal.organization_id
                return {
                    "effect": {
                        "fadeout": "slow",
                        "message": "Successfully Paid",
                        "type": "rainbow_man",
                    }
                }

            elif response.status_code == 401:
                self_rec = self.env["revenue.system.payment"].sudo().browse(self.id)
                self_rec.unlink()
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Error!",
                        "message": response_dict["Message"],
                        "type": "danger",
                    },
                }
        except Exception as e:
            self_rec = self.env["revenue.system.payment"].sudo().browse(self.id)
            self_rec.unlink()
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error!",
                    "message": f"Error Occurred While Making Payment!!--{e}",
                    "type": "danger",
                },
            }

    def print_receipt(self):
        payment_master = (
            self.env["organization.payment.master"]
            .sudo()
            .search([("token", "=", self.payment_token.token)])
        )
        payment_methods = (
            self.env["organization.payment.gateways"]
            .sudo()
            .search([("code", "=", "revenue")])
        )
        url = "http://kathmandu.acc.shangrilagroup.com.np///api/RevEndServices//EndPort/PrintReceiptReport"
        payload = json.dumps(
            {
                "receipt_no": self.tax_revenue_receipt_no,
                "external_receipt_no": payment_master.token,
                "report_with_external_receipt_no": True,
            }
        )
        headers = {
            "api_auto_auth": "true",
            "Authorization": payment_methods.merchant_api_key,
            "Content-Type": "application/json",
            "Cookie": "app1.acc.munerp=gupuu04wzbdbuqt25kwojt4v",
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            resp_text = response.text
            response_dict = json.loads(resp_text)
            if response.status_code == 200:
                self.tax_revenue_receipt_url = response_dict["report_url"]
                return {
                    "type": "ir.actions.act_url",
                    "url": response_dict["report_url"],
                    "target": "new",
                }
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Error!",
                        "message": "Error while processing the data, try again!",
                        "type": "danger",
                    },
                }
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error!",
                    "message": "Network Error! Check your connection and try again!",
                    "type": "danger",
                },
            }

    def mail_receipt(self):
        template_ref = self.env.ref(
            "organization_payments.organization_revenue_receipt"
        )
        try:
            template_ref.send_mail(self.id, force_send=True)
            return {
                "effect": {
                    "fadeout": "slow",
                    "message": f"Receipt Mail Sent to {self.client_id.login}",
                    "type": "rainbow_man",
                }
            }

        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error!",
                    "message": "Couldn't sent the email, Please try again!",
                    "type": "danger",
                },
            }


class PaymentRequirement(models.Model):
    _name = "payment.requirement"

    SELECTION_OPTIONS = [
        ("tole_bikash", "Tole Bikash"),
        ("organization", "Organization"),
        ("upabhokta_samiti", "Upabhokta Samiti"),
        ("org_d", "Org D"),
    ]
    is_payment_required = fields.Boolean(" Payment Require ")

    Organization_Type = fields.Selection(SELECTION_OPTIONS, string="Organization Type")

    payment_type_selection = fields.Many2many(
        "organization.register.renew", string="Payment Titles"
    )
    total_cost = fields.Integer("Total Cost", compute="_compute_total_cost", store=True)

    @api.depends("payment_type_selection.total_cost")
    def _compute_total_cost(self):
        for record in self:
            
            record.total_cost = record.payment_type_selection.total_cost

    @api.onchange("Organization_Type")
    def onchange_method_check(self):
        self._check_unique_name()

    # @api.constrains("Organization_Type")
    # def constraints_method_check(self):
    #     self._check_unique_name()

    def _check_unique_name(self):
        for record in self:
            if record.Organization_Type:
                filter_domain = [
                    ("Organization_Type", "=", self.Organization_Type),
                    ("create_uid", "=", self.env.user.id),
                ]
                _payment = self.env["payment.requirement"].sudo().search(filter_domain)
                if _payment:
                    raise ValidationError(f"The inserted record already exists!!")


class PaymentGateways(models.Model):
    _name = "organization.payment.gateways"
    _rec_name = "payment_method_name"

    payment_method_name = fields.Char("Payment Method")
    code = fields.Char()
    merchant_api = fields.Char("Merchant API")
    merchant_api_key = fields.Char("Merchant API Key")
    other_details = fields.Char("Other Details")


class OrganizationPaymentMaster(models.Model):
    _name = "organization.payment.master"
    _rec_name = "token"
    _description = "Payment Information"

    payment_method = fields.Many2one("organization.payment.gateways")
    payment_title = fields.Char("Payment title")
    client_id = fields.Many2one("res.users")
    organization_type = fields.Char("organization type")
    organization_id = fields.Integer()
    organization_name = fields.Char("Organization Name")
    amount = fields.Float("amount")
    transaction_date = fields.Char("transaction_date")
    transaction_id = fields.Char("transaction_id")
    payment_status = fields.Boolean(default=False)
    invoice_id = fields.Char("invoice_id")
    token = fields.Char("token")
    tax_revenue_receipt_no = fields.Char("tax_revenue_receipt_no")
    organization_registration_number = fields.Char("Registration Number")
    payment_for = fields.Selection(
        [("registration", "Registration"), ("renew", "Renew")]
    )
    remarks = fields.Char("remarks")
