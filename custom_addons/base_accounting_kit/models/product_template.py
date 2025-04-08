
from odoo import fields, models ,api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """Inherited the model for adding new fields and functions"""
    _inherit = 'product.template'

    asset_category_id = fields.Many2one(
        'account.asset.category', string='Asset Type',
        company_dependent=True, ondelete="restrict")
    deferred_revenue_category_id = fields.Many2one(
        'account.asset.category', string='Deferred Revenue Type',
        company_dependent=True, ondelete="restrict")

    # company_id = fields.Many2one(
    #     'res.company',
    #     string='Company',
    #     required=True,
    #     default=lambda self: self.env.company
    # )
    
    company_id = fields.Many2one('res.company', string='Company', required=False)

    business_based_products_id = fields.Many2one(
        'business.based.products',
        string='Products',
        domain="[('company_id', 'in', [company_id, 1])]"
    )

    name = fields.Char(string='Product Name', required=True)

    @api.constrains('name')
    def _check_unique_name(self):
        for product in self:
            if self.search([('name', '=', product.name), ('id', '!=', product.id)]):
                raise ValidationError('A product with this name already exists!')

    # # name = fields.Char(related="business_based_products_id.product_id.name", string="Product Name", store=True)
    @api.onchange('business_based_products_id')
    def _onchange_business_based_products_id(self):
        """ Update the name field based on selected business based product. """
        if self.business_based_products_id:
            print("==============================================",self.business_based_products_id.business_id.name)
            self.name = self.business_based_products_id.product_id.name
            self.company_category = self.business_based_products_id.business_id.id
        else:
            self.name = ''
            self.company_category = ''  


    @api.onchange('company_id')
    def _onchange_company_id(self):
        print("=========================",self.company_id.id)
        """ Update the domain for business_based_products_id based on the selected company. """
        if self.company_id:
            return {
                'domain': {
                    'business_based_products_id': [('business_id', '=', self.company_id.id)]
                }
            }
        else:
            return {'domain': {'business_based_products_id': []}}
   

    def _get_asset_accounts(self):
        res = super(ProductTemplate, self)._get_asset_accounts()
        if self.asset_category_id:
            res['stock_input'] = self.property_account_expense_id
        if self.deferred_revenue_category_id:
            res['stock_output'] = self.property_account_income_id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        # Set translations using context
        for record in records:
            if record.name_np:
                record.with_context(lang='ne_NP').write({
                    'name': record.name_np
                })
        
        return records
    
    def write(self, vals):
        res = super().write(vals)
        if 'name_np' in vals:
            for record in self:
                if record.name_np:
                    record.with_context(lang='ne_NP').write({
                        'name': record.name_np
                    })
        return res

class UomCategory(models.Model):
    """Inherited the model for adding new fields and functions"""
    _inherit = 'uom.category'
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        # Set translations using context
        for record in records:
            if record.name_np:
                record.with_context(lang='ne_NP').write({
                    'name': record.name_np
                })
        
        return records
    
    def write(self, vals):
        res = super().write(vals)
        if 'name_np' in vals:
            for record in self:
                if record.name_np:
                    record.with_context(lang='ne_NP').write({
                        'name': record.name_np
                    })
        return res
