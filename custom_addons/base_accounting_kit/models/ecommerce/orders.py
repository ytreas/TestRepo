from odoo import api, fields, models, _
import uuid
from datetime import datetime
import nepali_datetime
from .utils import NepalTZ
from odoo import http
from odoo.http import request



class EcommerceOrders(models.Model):
    _name = "ecommerce.orders"
    _description = "E-commerce Orders"

    user = fields.Many2one("res.users", string="User", required=True)
    name = fields.Char(
        string="Order Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    order_date = fields.Datetime(
        string="Order Date", default=lambda self: NepalTZ.get_nepal_time()
    )
    order_token = fields.Char(required=True, readonly=True, copy=False)
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("shipped", "Shipped"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
            ("refunded", "Refunded"),
            ("failed", "Failed"),
            ("abandoned", "Abandoned"),
        ],
        string="Status",
        default="pending",
        required=True,
    )
    order_line_ids = fields.Many2one("ecommerce.add.to.cart", string="Order")
    extra_charge = fields.Float("Extra Charge")
    extra_charge_title = fields.Html("Extra Charge Title")
    sale_order_id = fields.Char("Order ID")
    total_amount = fields.Float(
        string="Total Amount",
    )
    payment_method = fields.Selection(
        [
            ("khalti", "Khalti"),
            ("imepay", "Imepay"),
            ("esewa", "Esewa"),
            ("cod", "Cash on Delivery"),
        ]
    )
    payment_status = fields.Selection(
        [
            ("unpaid", "Unpaid"),
            ("paid", "Paid"),
        ],
        string="Payment Status",
        default="unpaid",
    )
    payment_master = fields.Many2one("ecommerce.payment.master")
    notes = fields.Text(string="Notes")
    order_common_token = fields.Char(required=True, readonly=True, copy=False)

    def get_my_order(self, common_order_token, user):
        my_order = self.search(
            [
                ("user", "=", user),
                ("order_common_token", "=", common_order_token),
                ("status", "in", ["pending", "processing", "shipped"]),
            ],
        )
        return my_order

    def get_my_orders(self, user, status="all"):
        domain = [
            ("user", "=", user),
        ]
        if status == "pending":
            domain.append(("status", "=", "pending"))
        if status == "processing":
            domain.append(("status", "=", "processing"))
        if status == "shipped":
            domain.append(("status", "=", "shipped"))
        if status == "delivered":
            domain.append(("status", "=", "delivered"))
        if status == "refunded":
            domain.append(("status", "=", "refunded"))
        if status == "cancelled":
            domain.append(("status", "=", "cancelled"))
        else:
            domain.append(
                (
                    "status",
                    "in",
                    [
                        "pending",
                        "processing",
                        "shipped",
                        "cancelled",
                        "refunded",
                        "delivered",
                    ],
                )
            )
        my_orders = self.search(domain, order="order_date desc")

        return my_orders

    def create(self, vals_list):
        vals_list = vals_list if isinstance(vals_list, list) else [vals_list]

        for vals in vals_list:
            vals["order_token"] = str(uuid.uuid4().int)[:30]

            if vals.get("name", _("New")) == _("New"):
                date_sequence = nepali_datetime.date.today().strftime("%Y%m%d")
                sequence_number = (
                    self.env["ir.sequence"].next_by_code("ecommerce.orders") or "00000"
                )
                vals["name"] = f"ORD-{date_sequence}-{sequence_number}"

            ecommerce_order = super(EcommerceOrders, self).create(vals)

        return ecommerce_order

    def get_company_logo(self):
        company = self.env["res.company"].sudo().search([], limit=1)
        return company


class SaleOrdersInherit(models.Model):
    _inherit = "sale.order"
    ecommerce_order_id = fields.Many2one("ecommerce.orders")

    def action_confirm(self):
        for rec in self:
            if not rec.ecommerce_order_id:
                pass
            else:
                ecommerce_order = self.env["ecommerce.orders"].browse(
                    rec.ecommerce_order_id.id
                )
                ecommerce_order.write({"status": "processing"})
        result = super(SaleOrdersInherit, self).action_confirm()
        return result
