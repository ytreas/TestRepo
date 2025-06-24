# models/transport_expense.py
from odoo import models, fields, api
from ..models.transport_order import convert_to_bs_date

class TransportExpense(models.Model):
    _name = 'transport.expense'
    _description = 'Trip Expense'
    _order = 'create_date desc'

    # Link to the related transport order
    order_id = fields.Many2one(
        'transport.order', string='Transport Order', required=True, ondelete='cascade'
    )

    # Type of expense being recorded
    expense_type = fields.Selection([
        ('fuel', 'Fuel'),
        ('toll', 'Toll'),
        ('maintenance', 'Maintenance'),
        ('allowance', 'Driver Allowance'),
    ], string='Expense Type', required=True)

    # Amount spent on the expense
    amount = fields.Monetary(string='Amount', required=True)
    fuel_volume = fields.Float(string='Total Fuel(liter)')

    show_field = fields.Boolean(string='Show Fuel Volume', default=False)
    @api.onchange('expense_type')
    def _compute_show_field(self):
        for record in self:
            print("Expense Type:", record.expense_type,record.show_field)
            record.show_field = record.expense_type == 'fuel'
    # Gregorian date of the expense
    date = fields.Date(
        string='Date', default=fields.Date.today, required=True
    )

    # BS (Nepali date) equivalent of the expense date (computed)
    date_bs = fields.Char(
        string='Date BS', compute='_compute_date_bs'
    )

    # Currency used for the expense, defaults to Nepali Rupee (NPR)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env['res.currency'].browse(117),
        readonly=True,
    )

    order_total = fields.Monetary(
        string='Order Total',
        compute='_compute_order_total',
        store=False,
        currency_field='currency_id'
    )

    @api.depends('order_id.expense_ids.amount')
    def _compute_order_total(self):
        for exp in self:
            if exp.order_id:
                exp.order_total = sum(exp.order_id.expense_ids.mapped('amount'))
            else:
                exp.order_total = 0.0

    @api.depends('date')
    def _compute_date_bs(self):
        """
        Compute the BS (Nepali) date equivalent for the expense date
        using a shared utility from the transport order module.
        """
        for record in self:
            record.date_bs = convert_to_bs_date(record.date) if record.date else False

 