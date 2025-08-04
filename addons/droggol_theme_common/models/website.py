# -*- coding: utf-8 -*-
# Copyright (c) 2019-Present Droggol. (<https://www.droggol.com/>)

import base64

from odoo import fields, models, tools
from odoo.modules.module import get_resource_path


class Website(models.Model):
    _inherit = 'website'

    def _default_footer_logo(self):
        image_path = get_resource_path('website', 'static/src/img', 'website_logo.png')
        with tools.file_open(image_path, 'rb') as f:
            return base64.b64encode(f.read())

    logo_footer = fields.Binary('Website Footer Logo', default=_default_footer_logo, help='Display this logo on the website footer.')
    zoom_factor = fields.Integer(default=3)
    dr_sale_special_offer = fields.Html(sanitize_attributes=False)

    # PWA
    has_pwa = fields.Boolean()
    pwa_name = fields.Char()
    pwa_short_name = fields.Char()
    pwa_background_color = fields.Char(default='#000000')
    pwa_theme_color = fields.Char(default='#FFFFFF')
    pwa_icon_192 = fields.Binary()
    pwa_icon_512 = fields.Binary()
    pwa_start_url = fields.Char(default='/shop')
    pwa_version = fields.Integer(default=1)
    pwa_offline_page = fields.Boolean()

    # eCommerce
    # TODO: in v14 uncomment this part and remove it from 'res.config.settings'
    # Put this field as related in the config ans remve config param.
    # dr_cart_flow = fields.Selection([
    #     ('default', 'Default'),
    #     ('notification', 'Show notification'),
    #     ('dialog', 'Show dialog'),
    #     ('side_cart', 'Open Cart Sidebar')],
    #     string="Add to cart flow",
    #     default='default'
    # )

    def _convert_currency_price(self, amount, from_base_currency=True, rounding_method=None):
        base_currency = self.company_id.currency_id
        pricelist_currency = self.get_current_pricelist().currency_id
        if base_currency != pricelist_currency:
            if from_base_currency:
                amount = base_currency._convert(amount, pricelist_currency, self.company_id, fields.Date.today())
            else:
                amount = pricelist_currency._convert(amount, base_currency, self.company_id, fields.Date.today())
        return rounding_method(amount) if rounding_method else amount

    def write(self, vals):
        pwa_fields = {'pwa_name', 'pwa_short_name', 'pwa_background_color', 'pwa_theme_color', 'pwa_icon_192', 'pwa_icon_512', 'pwa_start_url', 'pwa_offline_page'}
        if len(self) == 1 and vals.keys() & pwa_fields:
            vals['pwa_version'] = self.pwa_version + 1
        res = super(Website, self).write(vals)
        return res

    def _get_website_category(self):
        return self.env['product.public.category'].search([('website_id', 'in', [False, self.id]), ('parent_id', '=', False)])


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    website_logo_footer = fields.Binary(related='website_id.logo_footer', readonly=False)
    zoom_factor = fields.Integer(related='website_id.zoom_factor', readonly=False)

    # PWA
    website_has_pwa = fields.Boolean(related='website_id.has_pwa', readonly=False)
    website_pwa_name = fields.Char(related='website_id.pwa_name', readonly=False)
    website_pwa_short_name = fields.Char(related='website_id.pwa_short_name', readonly=False)
    website_pwa_background_color = fields.Char(related='website_id.pwa_background_color', readonly=False)
    website_pwa_theme_color = fields.Char(related='website_id.pwa_theme_color', readonly=False)
    website_pwa_icon_192 = fields.Binary(related='website_id.pwa_icon_192', readonly=False)
    website_pwa_icon_512 = fields.Binary(related='website_id.pwa_icon_512', readonly=False)
    website_pwa_start_url = fields.Char(related='website_id.pwa_start_url', readonly=False)
    website_pwa_offline_page = fields.Boolean(related='website_id.pwa_offline_page', readonly=False)

    # eCommerce
    # TODO: remove this in v14
    # dr_cart_flow = fields.Selection(related='website_id.dr_cart_flow', readonly=False)

    dr_cart_flow = fields.Selection([
        ('default', 'Default'),
        ('notification', 'Show notification'),
        ('dialog', 'Show dialog'),
        ('side_cart', 'Open Cart Sidebar')],
        string="Add to cart flow",
        default='default',
        config_parameter='dr_cart_flow'
    )
