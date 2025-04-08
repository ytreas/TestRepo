from odoo import models, fields

class CommodityPriceHistory(models.Model):
    _name = 'commodity.price.history'
    _description = 'Commodity Price History'

    commodity_name = fields.Char(string='Commodity', required=True)
    trader_1 = fields.Char(string='Trader 1')
    price_1 = fields.Float(string='Price 1')
    trader_2 = fields.Char(string='Trader 2')
    price_2 = fields.Float(string='Price 2')
    trader_3 = fields.Char(string='Trader 3')
    price_3 = fields.Float(string='Price 3')
    trader_4 = fields.Char(string='Trader 4')
    price_4 = fields.Float(string='Price 4')
    trader_5 = fields.Char(string='Trader 5')
    price_5 = fields.Float(string='Price 5')
    date = fields.Date(string='Date')

    def action_export_xlsx(self):
        """Search for the existing commodity price history Excel file and provide a download link."""
        attachment = self.env['ir.attachment'].search(
            [('name', '=', 'commodity_price_history_sample.xlsx')],
            limit=1
        )
        if attachment:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'File not found!',
                    'type': 'danger',
                    'sticky': False,
                }
            }
