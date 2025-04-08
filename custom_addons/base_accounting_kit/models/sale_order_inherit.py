# from odoo import api, models, fields, _
# import logging
# from odoo.exceptions import UserError, ValidationError
# from datetime import datetime
# import nepali_datetime
# _logger = logging.getLogger(__name__)

# class SaleOrderFiscal(models.Model):
#     _inherit = 'sale.order'

#     partner_id = fields.Many2one(
#         comodel_name='res.partner',
#         string="Customer",
#         required=True, change_default=True, index=True,
#         tracking=1,
#         domain="[('company_id', 'in', [False, company_id]),('is_company', '=', True)]")

#     @api.onchange('order_line')
#     def _onchange_order_line(self):
#         for line in self.order_line:

#             if line.product_type in ['service', 'consu']:
#                 continue
#             if line.product_id and line.product_uom_qty > line.product_id.qty_available:            
#                 raise ValidationError(
#                     _("You cannot sell %s because only %d are available in stock.") % (line.product_id.name, line.product_id.qty_available)
#                 )
#             # if virtual_available < 0:
#             #     raise ValidationError(
#             #         _("You cannot sell %s because its forecasted quantity is insufficient. Current forecasted quantity: %d. Required buffer: %d.") % (line.product_id.name, virtual_available, buffer_qty)
#             #     )
#             if line.product_id.custom_price_ids.saleable_qty:
#                 buffer_qty = line.product_id.qty_available - line.product_id.custom_price_ids.saleable_qty
#                 virtual_available = line.product_id.virtual_available - line.product_uom_qty
#                 if virtual_available < buffer_qty:
#                     raise ValidationError(
#                         # _("You cannot sell %s because forcasted %d is less than or equal to buffer %d") % (line.product_id.name, virtual_available, buffer_qty)
#                         _("You cannot sell %s because its forecasted quantity is insufficient. Current forecasted quantity: %d. On hand quantity: %d. Required buffer: %d. Saleable quantity: %d.") % (line.product_id.name, virtual_available, line.product_id.qty_available, buffer_qty, line.product_id.custom_price_ids.saleable_qty)
#                     )

#     @api.model
#     def _default_fiscal_year(self):
#         # Return the fiscal year set in the company
#         return (self.env.company.fiscal_year.id)

#     # Override the existing field to set a default value
#     fiscal_year = fields.Many2one(
#         'account.fiscal.year', 
#         default=_default_fiscal_year
#     )
    
#     @api.model
#     def get_partner_details(self,partner_id,type):
#         partner_address_np=''
#         partner_name_np=''
#         owner_name_np=''
        
#         partner_user=self.env['res.company'].sudo().search([('partner_id','=',int(partner_id))],limit=1)
#         if partner_user:
#             partner_address_np=partner_user.street_np
#             partner_name_np=partner_user.name_np
#             owner_name_np=partner_user.owner_name_np
            

#         if type=='partner_name':
#             return partner_name_np
        
#         if type=='partner_address':
#             return partner_address_np
#         if type=='partner_name_np':
#             return owner_name_np
        
        
#     @api.model
#     def get_date_bs(self,date):
#         try:
#             bs_date = nepali_datetime.date.from_datetime_date(date)
#             return bs_date
           
#         except Exception as e:
#             raise ValidationError(_("Invalid Date Type provided."))
        
        
    
# class PurchaseOrderFiscal(models.Model):
#     _inherit = 'purchase.order'

#     partner_id = fields.Many2one('res.partner', string='Vendor', required=True, change_default=True,    tracking=True, domain="[('is_company', '=', True),'|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="You can find a vendor by its Name, TIN, Email or Internal Reference.")

#     @api.model
#     def _default_fiscal_year(self):
#         # Return the fiscal year set in the company
#         return (self.env.company.fiscal_year.id)

#     # Override the existing field to set a default value
#     fiscal_year = fields.Many2one(
#         'account.fiscal.year', 
#         default=_default_fiscal_year
#     )

# class AccountMoveFiscal(models.Model):
#     _inherit = 'account.move'

#     invoice_date = fields.Date(
#         default=lambda self: fields.Date.today()
#     )

#     @api.model
#     def _default_fiscal_year(self):
#         return self.env.company.fiscal_year.id if self.env.company.fiscal_year else False
#         # pass

#     fiscal_year = fields.Many2one(
#         'account.fiscal.year',
#         default=_default_fiscal_year
#     )

#     date_range_fy_id = fields.Many2one(
#         'account.fiscal.year',
#         compute="_compute_date_range_fy_id", store=True
#     )

#     @api.depends('fiscal_year')
#     def _compute_date_range_fy_id(self):
#         for record in self:
#            record.date_range_fy_id = record.fiscal_year.id if record.fiscal_year else False
    
    
#     @api.model
#     def get_partner_details(self,partner_id,type=None):
#         print("partner",partner_id)
#         partner_address_np=''
#         partner_name_np=''
#         owner_name_np=''
        
#         partner_user=self.env['res.company'].sudo().search([('partner_id','=',int(partner_id))],limit=1)
#         print("partner user",partner_user)

#         if partner_user:
#             partner_address_np=partner_user.street_np
#             partner_name_np=partner_user.name_np
#             owner_name_np=partner_user.owner_name_np
            

#         if type=='partner_name':
#             return partner_name_np
        
#         if type=='partner_address':
#             return f"{partner_name_np} <br/> {partner_address_np}"
#         if type=='partner_name_np':
#             return owner_name_np
#         return partner_id
    
#     @api.model
#     def get_product_name_np(self, product_id):
#         print("product id",product_id)
#         product = self.env['product.template'].sudo().browse(product_id)
#         if product.exists():
#             product_name_np = product.name_np
#             print('product',product_name_np)
#             return product_name_np or ''
#         return ''