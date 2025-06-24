# models/transport_billing_rule.py
from odoo import models, fields

class TransportBillingRule(models.Model):
    _name = 'transport.billing.rule'
    _description = 'Billing Rule'
    _order = 'create_date desc'
    _rec_name = 'name'

    # Name of the billing rule
    name = fields.Char(string='Rule Name', required=True)

    # Type of rate to apply for billing
    rate_type = fields.Selection([
        ('fixed', 'Fixed'),       # Flat rate
        ('per_km', 'Per KM'),     # Based on distance
        ('per_ton', 'Per Ton'),   # Based on cargo weight
        ('per_hour', 'Per Hour'), # Based on time
    ], string='Rate Type', required=True)

    # Unit price according to the rate type
    unit_price = fields.Monetary(string='Unit Price', required=True)

    # Currency used for the pricing, defaulting to the company's currency
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id
    )
