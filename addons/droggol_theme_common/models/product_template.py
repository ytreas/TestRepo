# -*- coding: utf-8 -*-
# Copyright (c) 2019-Present Droggol. (<https://www.droggol.com/>)

from odoo import api, fields, models


class DrProductBrand(models.Model):
    _name = 'dr.product.brand'
    _inherit = ['website.multi.mixin']
    _description = 'Product Brand'

    name = fields.Char(required=True, translate=True)
    description = fields.Char(translate=True)
    image = fields.Binary()
    product_ids = fields.One2many('product.template', 'dr_brand_id')
    product_count = fields.Integer(compute='_compute_product_count')
    active = fields.Boolean(default=True)

    def _compute_product_count(self):
        for brand in self:
            brand.product_count = len(brand.product_ids)

    def action_open_products(self):
        self.ensure_one()
        action = self.env.ref('website_sale.product_template_action_website').read()[0]
        action['domain'] = [('dr_brand_id', '=', self.id)]
        action['context'] = {}
        return action


class DrProductLabel(models.Model):
    _name = 'dr.product.label'
    _inherit = ['website.multi.mixin']
    _description = 'Product Label'

    name = fields.Char(required=True, translate=True)
    color = fields.Selection([
        ('green', 'Green'),
        ('blue', 'Blue'),
        ('gray', 'Gray'),
        ('red', 'Red'),
        ('orange', 'Orange'),
        ('black', 'Black'),
    ])
    product_ids = fields.One2many('product.template', 'dr_label_id')
    product_count = fields.Integer(compute='_compute_product_count')

    def _compute_product_count(self):
        for label in self:
            label.product_count = len(label.product_ids)

    def action_open_products(self):
        self.ensure_one()
        action = self.env.ref('website_sale.product_template_action_website').read()[0]
        action['domain'] = [('dr_label_id', '=', self.id)]
        action['context'] = {}
        return action


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    dr_brand_id = fields.Many2one('dr.product.brand', string='Brand')
    dr_label_id = fields.Many2one('dr.product.label', string='Label')

    @api.onchange('website_id')
    def _onchange_website_id(self):
        self.dr_brand_id = False
        self.dr_label_id = False

    @api.model
    def _get_product_colors(self):
        color_variants = self.attribute_line_ids.filtered(lambda x: x.attribute_id.display_type == 'color')
        if len(color_variants) == 1:
            if len(color_variants.value_ids) == 1:
                return []
            return color_variants.value_ids.mapped('html_color')
        return []

    @api.model
    def _get_product_pricelist_offer(self):
        partner = self.env.context.get('partner')
        pricelist_id = self.env.context.get('pricelist')
        pricelist = self.env['product.pricelist'].browse(pricelist_id)

        price_rule = pricelist._compute_price_rule([(self, 1, partner)])
        price_rule_id = price_rule.get(self.id)[1]
        if price_rule_id:
            rule = self.env['product.pricelist.item'].browse([price_rule_id])
            if rule and rule.date_end:
                return {'rule': rule, 'date_end': rule.date_end.strftime("%Y-%m-%d") + ' 00:00:00'}
        return False


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    display_type = fields.Selection(
        selection_add=[
            ('radio_circle', 'Radio Circle'),
            ('radio_square', 'Radio Square'),
        ])
    dr_is_enable_shop_filter = fields.Boolean('Enable in Shop Filter', default=True)
    dr_is_enable_shop_search = fields.Boolean('Enable Search in Shop Filter', default=False)


class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    offer_msg = fields.Char('Offer Message', default='Hurry Up! Limited time offer', translate=True)
    offer_finish_msg = fields.Char('Offer Finish Message', default='Offer finished.', translate=True)
