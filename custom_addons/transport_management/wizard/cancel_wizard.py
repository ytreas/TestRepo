from odoo import models, fields, api
from ..utils.dashboard_notification import notify_transport

class CancelWizard(models.TransientModel):
    _name = 'cancel.wizard'
    _description = 'Cancel Order Wizard'

    reason = fields.Text(string='Reason for Cancellation', required=True)

    def confirm_cancel(self):
        active_id = self.env.context.get('active_id')
        order = self.env['transport.order'].browse(active_id)
        customer = self.env['customer.request.line'].search([('id', '=', order.request_line_id.id)], limit=1)
        if customer:
            customer.write({'state': 'cancelled', 'cancel_reason': self.reason})
        if order:
            order.write({'state': 'cancelled', 'cancel_reason': self.reason})

        mail_values = {
            'subject': 'Order Cancelled %s' % order.name,
            'body_html': (
                f'<p>Dear {order.customer_name.name},</p>'
                f'<p>We are pleased to inform you that your order <strong>{order.name}</strong> has been cancelled.</p>'
                f'<p>{self.reason}</p>'
                f'<p>Please placed order next time:</p>'
                f'<p>If you have any questions or need further assistance, please do not hesitate to contact us.</p>'
                f'<p>Thank you for choosing our services.</p>'
                f'<p>Best regards,</p>'
                f'<p>{self.env.company.name}</p>'
            ),
            'email_to': order.customer_name.email,
            'model': 'transport.order',
            'res_id': self.id,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()
        
        
        customer_name    = order.customer_name.name
        date             = order.order_date
        notify_transport(
            env=self.env,
            notification_type='cancel',
            customer_name=customer_name,
            order_name=order.name,
            date=date, 
            order_id=order.id,
        ) 
        