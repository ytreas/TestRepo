from odoo import models,fields,api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_view_purchase_order(self):
        # Find the related purchase order
        purchase_order = self.env['purchase.order'].sudo().search([('name', '=', self.origin)], limit=1)
        
        if purchase_order:
            # Use sudo to bypass access rights for the action
            action = self.env.ref('purchase.purchase_form_action').sudo().read()[0]
            action['views'] = [(self.env.ref('purchase.purchase_order_form').sudo().id, 'form')]
            action['res_id'] = purchase_order.id
            return action
        else:
            # If no purchase order found, return an empty dictionary or some feedback
            return {'type': 'ir.actions.act_window_close'}

