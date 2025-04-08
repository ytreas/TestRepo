
from odoo import fields, models


class RegisterPaymentWizard(models.TransientModel):
    """Details for a payment for parking"""
    _name = 'register.payment.wizard'
    _description = 'Register Parking Payment'

    # partner_id = fields.Many2one('res.partner',
    #                              string='Partner',
    #                              help='Name of partner to register the payment')
    parking_duration = fields.Float(string='Duration',
                                    help='Duration of the parking vehicle')
    amount = fields.Float(string='Amount',
                          help='Amount of the parking vehicle')
    ref = fields.Char(string='Reference',
                      help='Reference to the parking ticket')
    date = fields.Date(string='Date', default=fields.Date.context_today,
                       help='Date when payment was made')
    date_bs = fields.Char(string="Date BS")
    type_of_payment = fields.Selection([
        ('esewa', 'Esewa'),
        ('khalti', 'Khalti'),
        ('cash', 'Cash')
    ], string="Types of Payment", required= True, help="Select the type of payment")


    def parking_payment(self):
        """Returns the amount of the parking ticket for the customer."""
        active_id = self._context.get('active_id')

        active_record = self.env['amp.daily.arrival.entry'].browse(active_id)


        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            # 'partner_id': self.partner_id.id,
            'amount': self.amount,
            'ref': self.ref,
        })
        payment.action_post()

        active_record.write({
            'paid_bool': True,
            'state': 'payment',
            'check_out_bool': False,
            'check_in_bool': False,
            'type_of_payment': self.type_of_payment,
        })
        
        return {'type': 'ir.actions.act_window_close'}
