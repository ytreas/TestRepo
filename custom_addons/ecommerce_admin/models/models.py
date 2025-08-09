from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_delivered = fields.Boolean(
        string="Delivered",
        compute="_compute_is_delivered",
        store=True,
    )

    @api.depends('picking_ids.state')
    def _compute_is_delivered(self):
        for order in self:
            # Check if any related picking is done
            order.is_delivered = any(p.state == 'done' for p in order.picking_ids)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Force notification_type to 'inbox' always (fallback to 'email' if you want)
            vals['notification_type'] = 'inbox'
        return super().create(vals_list)
    def write(self, vals):
        if 'notification_type' in vals:
            if vals['notification_type'] not in ['email', 'inbox']:
                vals['notification_type'] = 'inbox'
        return super().write(vals)