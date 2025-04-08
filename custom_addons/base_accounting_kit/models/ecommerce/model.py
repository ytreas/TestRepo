from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
import math
from . import utils
import nepali_datetime
from datetime import date

class EcommerceOrders(models.Model):
    _name = "ecommerce.shipping.settings"
    _description = "E-commerce Cash Shipping Setting"

    code = fields.Char("Field Code", help="Unique Code. No spaces are allowed.")
    title = fields.Char("Field Name")
    fee = fields.Float("Fee")
    company_id = fields.Integer(
        "Company ID",
        tracking=True,
        default=lambda self: self.env.user.company_id,
        readonly=True,
    )


class EcommercePaymentMethods(models.Model):
    _name = "ecommerce.payment.methods"

    code = fields.Char("Code", required=True)
    name = fields.Char("Name", required=True)
    status = fields.Boolean(
        "Active",
        help="Allow this payment method in the e-commerce portal?",
        default=True,
    )
    company_id = fields.Integer(
        "Company ID",
        tracking=True,
        default=lambda self: self.env.user.company_id,
        readonly=True,
    )

    def get_allowed_methods(self):
        return self.search([("status", "=", True)]).mapped("code")


class EcommercePaymentCharges(models.Model):
    _name = "ecommerce.payment.charges"
    payment_method = fields.Many2one("ecommerce.payment.methods", "Payment Method")
    title = fields.Char("Fee Title")
    fee = fields.Float("Fee")
    company_id = fields.Integer(
        "Company ID",
        tracking=True,
        default=lambda self: self.env.user.company_id,
        readonly=True,
    )


DISTANCE_SELECTION = [
    ("10", "Below 10km"),
    ("20", "Below 20km"),
    ("30", "Below 30km"),
    ("40", "Below 40km"),
    ("50", "Below 50km"),
    ("60", "Below 60km"),
    ("70", "Below 70km"),
    ("80", "Below 80km"),
    ("90", "Below 90km"),
    ("100", "Below 100km"),
    ("110", "Below 110km"),
    ("120", "Below 120km"),
    ("130", "Below 130km"),
    ("140", "Below 140km"),
    ("150", "Below 150km"),
    ("160", "Below 160km"),
    ("170", "Below 170km"),
    ("180", "Below 180km"),
    ("190", "Below 190km"),
    ("200", "Below 200km"),
]


class EcommerceDeliveryCharges(models.Model):
    _name = "ecommerce.delivery.charges"
    _rec_name = "distance_below"

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    distance_below = fields.Selection(
        DISTANCE_SELECTION,
        help=_("This charge is applied to the distance upto this distance"),
    )
    distance_below_numeric = fields.Integer(
        compute="_compute_distance_below_numeric", store=True
    )

    @api.depends("distance_below")
    def _compute_distance_below_numeric(self):
        for rec in self:
            rec.distance_below_numeric = (
                int(rec.distance_below) if rec.distance_below else 0
            )

    delivery_charge = fields.Integer("Delivery Charge")
    delivery_type = fields.Selection(
        [
            ("standard", "Standard"),
            ("express", "Express"),
            ("same_day", "Same Day"),
            ("pickup", "Pickup"),
        ],
        string="Delivery Type",
        default="standard",
        required=True,
    )
    is_active = fields.Boolean(string="Is Active?", default=True)
    weight_limit = fields.Float(string="Weight Limit (kg)")
    additional_charge_per_kg = fields.Float(string="Additional Charge Per Kg")
    # distance_limit = fields.Float(string="Distance Limit (km)")
    priority = fields.Integer(string="Priority", default=10)
    free_over = fields.Boolean("Free if order amount is above?")
    free_delivery_threshold = fields.Float(_("Rs"))
    notes = fields.Html("Any notes?")

    # To be set by super admin
    max_price = fields.Integer("Max Price")
    min_price = fields.Integer("Min Price")

    @api.onchange("delivery_charge")
    def _calculate_delivery_charge(self):
        for rec in self:
            closest_charge = self.search(
                [
                    ("free_over", "=", None),
                    ("delivery_type", "=", rec.delivery_type),
                    ("distance_below_numeric", ">=", int(rec.distance_below)),
                ],
                order="distance_below_numeric asc",
                limit=1,
            )
            if closest_charge:
                if rec.delivery_charge > closest_charge.max_price:
                    raise ValidationError(
                        f"{_('Delivery charge cannot be more than')} {closest_charge.max_price} {_('for the distance below')} {closest_charge.distance_below} {_('km')}",
                    )
            pass

    def create(self, vals_list):
        vals_list = vals_list if isinstance(vals_list, list) else [vals_list]
        for vals in vals_list:
            closest_charge = self.search(
                [
                    ("free_over", "=", None),
                    ("delivery_type", "=", vals.get("delivery_type")),
                    ("distance_below_numeric", ">=", int(vals.get("distance_below"))),
                ],
                order="distance_below_numeric asc",
                limit=1,
            )
            if closest_charge:
                if vals.get("delivery_charge") > closest_charge.max_price:
                    raise ValidationError(
                        f"{_('Delivery charge cannot be more than')} {closest_charge.max_price} {_('for the distance below')} {closest_charge.distance_below} {_('km')}",
                    )
        return super().create(vals_list)
            
    def get_delivery_charge(self, company_id, lat2, lon2):
        company = self.env["res.company"].sudo().browse(company_id)
        lat1, lon1 = company.latitude, company.longitude
        distance = self.get_calculated_distance(lat1, lon1, lat2, lon2)

        closest_charge = self.search(
            [
                ("free_over", "!=", None),
                ("company_id", "=", company_id),
                ("distance_below_numeric", ">=", int(distance)),
            ],
            order="distance_below_numeric asc",
            limit=1,
        )
        if closest_charge:
            return closest_charge.delivery_charge
        return 500

    def get_calculated_distance(self, lat1, lon1, lat2, lon2):

        R = 6371

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance


class EcommerceSettingsMain(models.Model):
    _name = "ecommerce.main.settings"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    enable_delivery_charge = fields.Boolean("Enable delivery charge", default=False)
    enable_voucher = fields.Boolean("Enable Voucher", default=False)
    voucher_code = fields.Char("Voucher Code")
    color_theme = fields.Integer("My Vendor Page Color")

    def get_config(self, company_id=None):
        if not company_id:
            return None
        company = self.search(
            [("company_id", "=", company_id)], limit=1, order="id desc"
        )
        return {
            "enable_delivery_charge": company.enable_delivery_charge,
            "enable_voucher": company.enable_voucher,
            "color_theme": company.color_theme,
            "voucher_code": company.voucher_code,
        }


class ResCompanyInheritAddress(models.Model):
    _inherit = "res.company"

    pickup_location = fields.Char()
    latitude = fields.Float()
    longitude = fields.Float()

    def get_current_host_company(self):
        origin_url = utils.EcomUtils.get_current_origin()
        parent_company = (
            self.env["res.company"]
            .sudo()
            .search([("website", "=", origin_url["origin_url"])], limit=1)
        )
        return parent_company
    
    def ad_to_bs(self,ad_date):
      try:
        date_string=''.join(ad_date)
        ad_year, ad_month, ad_day = map(int, date_string.split('-'))
        ad_date = date(ad_year, ad_month, ad_day)
        bs_date = nepali_datetime.date.from_datetime_date(ad_date)
        return bs_date
    
      except Exception as e:
            return ad_date


class ProductCategoriesInherit(models.Model):
    _inherit = "product.category"

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.user.company_id
    )
