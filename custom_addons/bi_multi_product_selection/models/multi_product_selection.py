from odoo import _, api, fields, models 
import ast

class SaleOder(models.Model):

    _inherit = 'sale.order'

    product_ids = fields.Many2many('product.product',string="Select Product", required=True)
    partner_id = fields.Many2one(string='Customer', comodel_name='res.partner', ondelete='restrict',required=True)

    def sale_order_select_prodcut(self):
        wizard = self.env['sale.order.wizard'].create({
        'product_ids': self.product_ids.name  })
   
        return {
        'name': _('Select Product'),
        'type': 'ir.actions.act_window',  
        'res_model': 'sale.order.wizard',    
        'view_mode': 'form',  
        'res_id': wizard.id,  
        'target': 'new',
        }

class PurhcaseOrder(models.Model):

    _inherit = 'purchase.order'

    product_ids = fields.Many2many('product.product',string="Select Product",required=True)
    partner_id = fields.Many2one(string='Customer', comodel_name='res.partner', ondelete='restrict')

    def purchase_order_select_prodcut(self):
        print("here")
        if self.purchase_domain:
            purchase_domain = ast.literal_eval(self.purchase_domain)
            products = self.env['product.product'].search(purchase_domain)
            for product in products:
                product.temp_price = product.get_custom_price(self.partner_id)
                product.temp_quantity = product.sudo().get_custom_saleable_quantity(self.partner_id)
        wizard = self.env['purchase.order.wizard'].create({
        'product_ids': self.product_ids.name  })
   
        return {
        'name': _('Select Product'),
        'type': 'ir.actions.act_window',  
        'res_model': 'purchase.order.wizard',    
        'view_mode': 'form',  
        'res_id': wizard.id,  
        'target': 'new',
        'context': {
            'purchase_domain': self.purchase_domain,
        },
        }

class AccountMove(models.Model):

    _inherit = 'account.move'

    product_ids = fields.Many2many('product.product',string="Select Product",required=True)
    partner_id = fields.Many2one(string='Customer', comodel_name='res.partner', ondelete='restrict')

    def invoice_select_prodcut(self):
        wizard = self.env['account.move.wizard'].create({
        'product_ids': self.product_ids.name  })
   
        return {
        'name': _('Select Product'),
        'type': 'ir.actions.act_window',  
        'res_model': 'account.move.wizard',    
        'view_mode': 'form',  
        'res_id': wizard.id,  
        'target': 'new'
        }

class StockPicking(models.Model):

    _inherit = 'stock.picking'

    product_ids = fields.Many2many('product.product',string="Select Product", required=True)
    partner_id = fields.Many2one(string='Customer', comodel_name='res.partner', ondelete='restrict')

    def stock_picking_select_prodcut(self):
        wizard = self.env['stock.picking.wizard'].create({
        'product_ids': self.product_ids.name  })
   
        return {
        'name': _('Select Product'),
        'type': 'ir.actions.act_window',  
        'res_model': 'stock.picking.wizard',    
        'view_mode': 'form',  
        'res_id': wizard.id,  
        'target': 'new',
        'context': {'default_active_id': self.id},
        }
