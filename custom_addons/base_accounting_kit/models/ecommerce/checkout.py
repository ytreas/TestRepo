from odoo import api, fields, models, _
import uuid
from .utils import NepalTZ

class EcommerceCart(models.Model):
    _name = "ecommerce.checkout"
    _description = "E-commerce Checkout"

    user_id = fields.Many2one("res.users", string="User", required=True)
    checkout_order_token = fields.Char(required=True, readonly=True, copy=False)
    payment_token = fields.Char(readonly=True, copy=False)
    status = fields.Selection(
        [("active", "Active"), ("purchased", "Purchased"), ("abandoned", "Abandoned")],
        string="Status",
        default="active",
    )
    price_total = fields.Float("price total")
    added_date = fields.Datetime(string="Added Date", default=lambda self: NepalTZ.get_nepal_time())
    cart_item_ids = fields.Many2many(
        "ecommerce.add.to.cart",
        "checkout_cart_rel",
        "checkout_id",
        "cart_id",
        string="Cart IDS",
    )
    billing_address = fields.Html("Billing address")
    pickup_type = fields.Selection(
        [
            ("shipping", "Shipping"),("onsitepickup", "Onsite Pickup"),
        ]
    )
    pickup_address = fields.Html("Shipping address")
    notes = fields.Text(string="Notes")

    def create(self, vals_list):
        for vals in vals_list if isinstance(vals_list, list) else [vals_list]:
            vals["checkout_order_token"] = str(uuid.uuid4().int)[:30]
        return super().create(vals_list)
