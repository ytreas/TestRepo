from odoo import models, fields, api


class CompanyCategoryProduct(models.Model):
    _inherit = 'product.template'

    company_category = fields.Many2many('company.category',string='Company Category', readonly = True)
    name_np = fields.Char(string="Product Name (Nepali)")

    @api.onchange('business_based_products_id')
    def _onchange_business_based_products_id(self):
        # Clear the company_category field properly
        self.company_category = [(5, 0, 0)]  # This will clear the field
