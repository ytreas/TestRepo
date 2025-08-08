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
