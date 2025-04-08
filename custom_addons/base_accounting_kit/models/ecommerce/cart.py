from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from .utils import NepalTZ

class EcommerceCart(models.Model):
    _name = "ecommerce.add.to.cart"
    _description = "Ecommerce Add to Cart"

    user_id = fields.Many2one("res.users", string="User", required=True)
    product_id = fields.Many2one(
        "product.custom.price", string="Product", required=True,
    )
    quantity = fields.Integer(string="Quantity", default=1, required=True)
    price_unit = fields.Float(
        string="Unit Price",required=True
    )
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)
    status = fields.Selection(
        [("active", "Active"), ("purchased", "Purchased"), ("abandoned", "Abandoned")],
        string="Status",
        default="active",
    )
    added_date = fields.Datetime(string="Added Date", default=lambda self: NepalTZ.get_nepal_time())

    # TODO: Implement session tracking for product recommendations
    # session_id = fields.Many2one('', string="Session")
    cart_attribute_ids = fields.One2many(
        "ecommerce.cart.attributes", "cart_id", string="Cart Attributes"
    )

    notes = fields.Text(string="Notes")

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for record in self:
            record.subtotal = record.quantity * record.price_unit


    def get_individual_cart_quantity(self, product_id,user_id=None):
        total_quantity = (
            self.env["ecommerce.add.to.cart"]
            .sudo()
            .search(
                [
                    ("user_id", "=", user_id or self.env.user.id),
                    ("status", "=", "active"),
                    ("product_id", "=", product_id),
                    ("quantity", ">", 0),
                ]
            )
            .mapped("quantity")
        )

        return sum(total_quantity)

    def get_my_cart(self, user_id):

        domain = [('status','=','active')]
        if user_id:
            domain.append(("user_id", "=", user_id))
        my_cart = self.search(domain)
        return my_cart

    def get_related_companies(self, user_id):
        domain = [('status','=','active')]
        if user_id:
            domain.append(("user_id", "=", user_id))
        my_cart = self.search(domain)

        company_ids = my_cart.mapped("product_id.company_id.id")
        unique_company_records = self.env["res.company"].browse(list(set(company_ids)))

        return unique_company_records

    def get_related_companies_by_cart_ids(self, user_id, items):
        domain = []
        if user_id:
            domain.append(("user_id", "=", user_id))
        if items:
            domain.append(("id", "in", items.ids))

        my_cart = self.search(domain)

        company_ids = my_cart.mapped("product_id.company_id.id")
        unique_company_records = self.env["res.company"].browse(list(set(company_ids)))

        return unique_company_records

    def get_carts_by_ids(self, cart_ids):
        return self.search([("id", "in", cart_ids)])

    def deactivate_cart(self, cart_ids):
        try:
            self.search([("id", "in", cart_ids)]).write(
                {
                    "status": "purchased",
                }
            )
        except Exception as e:
            raise ValidationError(_("Cannot deactivate cart at the moment"))


class EcommerceCartAttributes(models.Model):
    _name = "ecommerce.cart.attributes"
    _description = "Ecommerce Add to Cart Attributes"

    cart_id = fields.Many2one(
        "ecommerce.add.to.cart", string="Cart", required=True, ondelete="cascade"
    )
    attribute_id = fields.Many2one("cp.attribute", string="Attribute", required=True)
    value_id = fields.Many2one("cp.attribute.value", string="Value", required=True)


class InheritWebsite(models.Model):
    _inherit = "website"

    def get_cart_quantity(self,user_id=None):

        total_quantity = (
            self.env["ecommerce.add.to.cart"]
            .sudo()
            .search(
                [
                    ("user_id", "=", user_id or self.env.user.id),
                    ("status", "=", "active"),
                    ("quantity", ">", 0),
                ]
            )
            .mapped("quantity")
        )

        return sum(total_quantity)
