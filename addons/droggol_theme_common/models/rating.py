# -*- coding: utf-8 -*-
# Copyright (c) 2019-Present Droggol. (<https://www.droggol.com/>)

from odoo import api, fields, models


class DrRating(models.Model):
    _inherit = 'rating.rating'

    dr_is_varified = fields.Boolean(string="Verified", default=False)

    @api.model
    def create(self, values):
        rating = super(DrRating, self).create(values)
        if rating.res_model and rating.res_model == 'product.template':
            orders = self.env['sale.order'].search([('partner_id', '=', rating.partner_id.id), ('state', 'in', ['done', 'sale'])])
            lines = self.env['sale.order.line'].search([('order_id', 'in', orders.ids), ('product_template_id', '=', rating.res_id)])
            if lines:
                rating.dr_is_varified = True
        return rating


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _message_read_dict_postprocess(self, message_values, message_tree):
        """ Override the method to add information about a publisher comment
        on each rating messages if requested, and compute a plaintext value of it.
        """
        res = super(MailMessage, self)._message_read_dict_postprocess(message_values, message_tree)

        if self._context.get('rating_include'):
            infos = ["dr_is_varified", "message_id"]
            related_rating = self.env['rating.rating'].search([('message_id', 'in', self.ids)]).read(infos)
            mid_rating_tree = dict((rating['message_id'][0], rating) for rating in related_rating)
            for values in message_values:
                values["is_varified_rating"] = mid_rating_tree.get(values['id'], {}).get('dr_is_varified')
        return res
