from odoo import api, fields, models
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class PurchaseFiscalYear(models.Model):
    _inherit = "purchase.order"
    _description = "Fiscal Year For Purchase"

    fiscal_year = fields.Many2one(
        'account.fiscal.year', 
        string='Fiscal Year', 
        default=lambda self: self._compute_fiscal_year()
    )
    # vendor_stock_info = fields.Text(
    #     string="Vendor Stock Information",
    #     compute="_compute_vendor_stock_info",
    #     readonly=True,
    # )
    # vendor_price_info = fields.Text(  # Changed to Text to support multiline text
    #     string="Vendor Price Information", 
    #     compute="_compute_vendor_price_info", 
    #     readonly=True
    # )

    vendor_stock_info = fields.Text(
        string="Vendor Stock Information",
        readonly=True,
    )
    vendor_price_info = fields.Text(  # Changed to Text to support multiline text
        string="Vendor Price Information", 
        readonly=True
    )

    @api.depends("date_order")
    def _compute_fiscal_year(self):
        current_date = self.date_order
        fiscal_year = self.env['account.fiscal.year'].search([
            ('date_from', '<=', current_date), 
            ('date_to', '>=', current_date)
        ], limit=1)
        if fiscal_year:
            return fiscal_year.id
        else:
            return False

    # @api.depends('partner_id')
    # def _compute_vendor_stock_info(self):
    #     for order in self:
    #         stock_info = ""
    #         if order.partner_id:
    #             _logger.info(f"Selected Vendor: {order.partner_id.name}")

    #             company_ids = order.partner_id.ref_company_ids.ids
    #             _logger.info(f"Related Company IDs for Vendor: {company_ids}")

    #             quants = self._get_stock_quantities(company_ids)
    #             _logger.info(f"Found {len(quants)} stock.quant records for related companies.")

    #             for quant in quants:
    #                 stock_info += f"Product: {quant.product_id.display_name}, Location: {quant.location_id.display_name}, Quantity: {quant.quantity}\n"
    #                 _logger.info(f"Product: {quant.product_id.display_name}, Location: {quant.location_id.display_name}, Quantity: {quant.quantity}")

    #         order.vendor_stock_info = stock_info
    #         _logger.info(f"Computed Stock Info: {stock_info}")

    # def _get_stock_quantities(self, company_ids):
    #     """ Helper method to retrieve stock quantities for given company IDs, excluding virtual locations. """
    #     stock_quants = []
    #     if company_ids:
    #         for company_id in company_ids:
    #             _logger.info(f"Searching stock.quants for company ID: {company_id}")
    #             quants = self.env['stock.quant'].search([
    #                 ('company_id', '=', company_id),
    #                 ('location_id.usage', '=', 'internal')
    #             ])
    #             _logger.info(f"Found {len(quants)} quants for company ID {company_id} after filtering out virtual locations.")
    #             stock_quants.extend(quants)
    #     return stock_quants

    # @api.onchange('partner_id')
    # def _onchange_partner_id(self):
    #     if self.partner_id:
    #         self._compute_vendor_stock_info()


    # @api.depends('order_line.product_id')
    # def _compute_vendor_price_info(self):
    #     # Cache for vendor-product price information
    #     price_cache = {}

    #     for order in self:
    #         price_info = ""
    #         for line in order.order_line:
    #             product_id = line.product_id.product_tmpl_id.id
    #             vendor_id = order.partner_id.id

    #             # Check cache first
    #             if (product_id, vendor_id) in price_cache:
    #                 price, saleable_qty = price_cache[(product_id, vendor_id)]
    #             else:
    #                 # If not in cache, fetch from API (consider batching if supported)
    #                 base = 'localhost:8069'
    #                 url = f'http://{base}/trading/api/get_vendor_price'
    #                 headers = {
    #                     'Content-Type': 'application/json',
    #                 }
    #                 data = {
    #                     'product_id': product_id,
    #                     'vendor_id': vendor_id,
    #                 }
    #                 response = requests.get(url, headers=headers, params=data)
    #                 response_text = json.loads(response.text)

    #                 price = response_text.get('price_sell')
    #                 saleable_qty = response_text.get('saleable_qty')

    #                 # Cache the result
    #                 price_cache[(product_id, vendor_id)] = (price, saleable_qty)

    #             product_name = line.product_id.display_name
    #             if price and saleable_qty:
    #                 price_info += f"{product_name} - price : {price} , saleable qty : {saleable_qty} \n"
    #             else:
    #                 price_info += f"{product_name} - price : {price} , saleable qty : {saleable_qty} \n"

    #         order.vendor_price_info = price_info
    #         _logger.info(f"Computed Vendor Price Info for order {order.id}: {order.vendor_price_info}")
