from odoo import models, fields


class UserActivityLog(models.Model):
    _name = "user.activity.log"
    _description = "User Activity Log"

    user_id = fields.Many2one("res.users", string="User")
    session_id = fields.Char(string="Session ID")
    country_name = fields.Char(string="Country Name")
    country_code = fields.Char(string="Country Code")
    request_ip = fields.Char(string="Request IP Address")
    product_id = fields.Many2one("product.custom.price", string="Product")
    vendor_id = fields.Many2one("res.company", string="Vendor")
    activity_type = fields.Selection(
        [
            ("view", "Viewed"),
            ("cart", "Added to Cart"),
            ("purchase", "Purchased"),
            ("search", "Searched"),
        ],
        string="Activity Type",
        required=True,
    )
    search_query = fields.Char(string="Search Query")
    timestamp = fields.Datetime(
        string="Timestamp", default=fields.Datetime.now, readonly=True, index=True
    )
