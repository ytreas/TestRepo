from odoo import api, fields, models, tools, _


class UserShippingAddress(models.Model):
    _name = "ecommerce.user.address"

    user = fields.Many2one("res.users", "User")
    fullname = fields.Char("Fullname")
    phone_number = fields.Char("Phone Number", max_length=10)
    email = fields.Char("Email")
    street = fields.Char("Building / House No / Floor / Street")
    address = fields.Char("Address")
    type = fields.Selection(
        [
            ("shipping", "Shipping"),
            ("invoicing", "Invoicing"),
        ]
    )
    selected = fields.Boolean("selected", default=False)

    def get_addresses(self, user, address_type):
        domain = []
        if user:
            domain.append(("user", "=", user))
        if address_type:
            domain.append(("type", "=", address_type))

        addresses = self.search(domain)
        return addresses

    def get_default_address(self, address_type, user_id):
        domain = [("user", "=", user_id)]

        if address_type == "billing":
            domain.append(("type", "=", "invoicing"))
        elif address_type == "shipping":
            domain.append(("type", "=", "shipping"))
            domain.append(("selected", "=", True))

        return self.search(domain)


class ResPartnerAddress(models.Model):
    _inherit = "res.partner"
    address_selected = fields.Boolean("selected", default=False)

    def get_addresses(self, user, address_type):
        domain = []
        if user:
            domain.append(("commercial_partner_id", "=", user))
        if address_type:
            domain.append(("type", "=", address_type))

        addresses = self.search(domain)
        return addresses

    def get_default_address(self, address_type, user_id):
        domain = [("commercial_partner_id", "=", user_id)]

        if address_type == "billing":
            domain.append(("type", "=", "contact"))
        elif address_type == "shipping":
            domain.append(("type", "=", "delivery"))
            domain.append(("address_selected", "=", True))

        return self.search(domain)
