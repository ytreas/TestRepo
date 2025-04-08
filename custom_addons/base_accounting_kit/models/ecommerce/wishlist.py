from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from .utils import NepalTZ

class EcommerceWishlist(models.Model):
    _name = "ecommerce.wishlist"
    _description = "E-commerce Wishlist"

    user_id = fields.Many2one("res.users", string="User", required=True)
    product_id = fields.Many2one("product.custom.price", string="Product", required=True)
    added_date = fields.Datetime(string="Added Date", default=lambda self: NepalTZ.get_nepal_time())
    

    # TODO: Implement session tracking for product recommendations
    # session_id = fields.Many2one('', string="Session")
    wishlist_attribute_ids = fields.One2many(
        "ecommerce.wishlist.attributes", "wishlist_id", string="Wishlist Attributes"
    )
    notes = fields.Text(string="Notes")

    def check_if_wishlist_exists(self, product_id):
        wishlist_entry = (
            self.env["ecommerce.wishlist"]
            .sudo()
            .search_count(
                [
                    ("user_id", "=", self.env.user.id),
                    ("product_id", "=", product_id),
                ]
            )
        )
        return wishlist_entry > 0
    def wishlist_count(self, product_id):
        count = (
            self.env["ecommerce.wishlist"]
            .sudo()
            .search_count(
                [
                    ("product_id", "=", product_id),
                ]
            )
        )
        return count 

    def get_wishlist(self,user_id = False):
        wishlist = (
            self.env["ecommerce.wishlist"]
            .sudo()
            .search_count(
                [
                    ("user_id", "=", self.env.user.id),
                ]
            )
        )
        
        return wishlist
    
    def get_wishlist_record(self,user_id):
        wishlist = (
            self.env["ecommerce.wishlist"]
            .sudo()
            .search(
                [
                    ("user_id", "=", user_id),
                ]
            )
        )
        return wishlist
    
    def get_related_companies(self, user_id):
        domain = []
        if user_id:
            domain.append(("user_id", "=", user_id))
        my_wishlist = self.search(domain)

        company_ids = my_wishlist.mapped("product_id.company_id.id")
        unique_company_records = self.env["res.company"].browse(list(set(company_ids)))

        return unique_company_records


class EcommerceWishlistAttributes(models.Model):
    _name = "ecommerce.wishlist.attributes"
    _description = "Ecommerce Add to Wishlist Attributes"

    wishlist_id = fields.Many2one(
        "ecommerce.wishlist", string="Wishlist", required=True, ondelete="cascade"
    )
    attribute_id = fields.Many2one("cp.attribute", string="Attribute", required=True)
    value_id = fields.Many2one("cp.attribute.value", string="Value", required=True)
