from odoo import api, fields, models, _
import uuid
from datetime import datetime
import nepali_datetime


class EcommercePayment(models.Model):
    _name = "ecommerce.payment.master"
    _description = "E-commerce Payment"

    name = fields.Char(
        string="Payment Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    user = fields.Many2one(
        "res.partner",
        default=lambda self: self.env.user.partner_id.id,
    )
    payment_method = fields.Selection(
        [
            ("khalti", "Khalti"),
            ("imepay", "Imepay"),
            ("esewa", "Esewa"),
            ("cod", "Cash on Delivery"),
        ]
    )
    amount = fields.Float("Amount", store=True)
    tax_amount = fields.Float("Tax amount", store=True)
    total_amount = fields.Float("Total Amount", store=True)

    transaction_date = fields.Datetime(
        string="Transaction Date", default=fields.Datetime.now
    )
    transaction_token = fields.Char("Transaction Token", store=True)

    payment_status = fields.Boolean(default=False)
    order_id = fields.Many2one("ecommerce.orders", string="Order ID", store=True)
    remarks = fields.Char("Remarks", store=True)

    company_id = fields.Integer(
        "Company ID",
        tracking=True,
        default=lambda self: self.env.user.company_id,
        readonly=True,
    )
    payment_success_from_provider = fields.Boolean(default=False)

    def create(self, vals_list):
        vals_list = vals_list if isinstance(vals_list, list) else [vals_list]
        for vals in vals_list:
            vals["transaction_token"] = str(uuid.uuid4().int)[:30]
            if vals.get("name",_("New")) == _("New"):
                date_sequence = nepali_datetime.date.today().strftime("%Y%m%d")
                sequence_number = (
                    self.env["ir.sequence"].next_by_code("ecommerce.payment.master")
                    or "00000"
                )
                vals["name"] = f"PMT-{date_sequence}-{sequence_number}"

        return super().create(vals_list)
