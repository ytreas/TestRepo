from odoo import models, fields, api , _
from datetime import datetime, timedelta
from odoo.exceptions import UserError 
import logging
import base64

_logger = logging.getLogger(__name__)

class FinalInvoiceWizard(models.TransientModel):
    _name = 'invoice.wizard'
    _description = 'Final Invoice Wizard'

    invoice_date = fields.Date(string="Invoice Date",readonly=True, default=fields.Date.today())
    customer = fields.Many2one('res.partner', string="Customer",readonly=True)
    total_amount = fields.Float(string="Total Amount")
    amount = fields.Float(string="Amount")
    invoice_type = fields.Selection([
        ('advance', 'Advance'),
        ('final', 'Final')
    ], string="Invoice Type", readonly=True)
    tax_id = fields.Many2one('account.tax', string="Tax", readonly=True)
    tax_amount = fields.Float(string="Tax Amount", readonly=True)
    invoice_id = fields.Many2one('account.move', string="Invoice")
    payment_id = fields.Many2one('account.payment', string="Payment")
    # final_invoice_id = fields.Many2one('account.move', string="Final Invoice")
    request_line_id = fields.Many2one('customer.request.line', string="Line ID")
    payment_type = fields.Selection([
        ('online', 'Online Payment'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('other', 'Other'),
    ], string="Payment Type", required=True, default='cash')
    remarks = fields.Text(string="Remarks")
    def make_invoice(self):
        print("self", self.request_line_id)
        for record in self:
            if record.payment_type == 'bank_transfer':
                journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
            else:
                journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
                print("journal", journal.name,journal.id)
            # partner = record.customer
            if record.invoice_type == 'advance': 
                payment_vals = {
                    'partner_id': record.customer.id,
                    'amount': record.amount,
                    'currency_id': 117,
                    'payment_type': 'inbound',
                    'journal_id': journal.id,
                    # 'move_id': record.invoice_id.id,
                    'ref': record.remarks,

                }
                payment = self.env['account.payment'].create(payment_vals)
                request_line = self.env['customer.request.line'].search([('id', '=', record.request_line_id.id)])
                order = self.env['transport.order'].search([('request_line_id', '=', record.request_line_id.id)],limit=1)
                request_line.write({
                    'payment_id': payment.id,
                    'payment_state': 'advance',
                    'state': 'advance',
                    })
                order.write({
                    'advance_done':True,
                })
                
                if payment:
                    payment.action_post()

                
                payment = self.env['account.payment'].browse(payment.id)
                invoice = self.env['account.move'].browse(record.invoice_id.id)
                #     ('line_ids.move_id', '=', 98),
                #     ('line_ids.account_id.reconcile', '=', True),  # Only reconcilable accounts
                #     # ('full_reconcile_id', '=', False),
                # ])
                if not payment.move_id or not invoice.exists():
                    raise UserError("Missing accounting entries")
                
                payment_line = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                    and not l.reconciled
                )
                
                invoice_line = invoice.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                    and not l.reconciled
                )
                print("payment_line", payment_line)
                print("invoice_line", invoice_line)
                # Reconcile
                if payment_line and invoice_line:
                    (payment_line + invoice_line).reconcile()
                    # This should be triggered after payment is validated/reconciled
                    # report = self.env['ir.actions.report']._get_report_from_name('transport_management.report_invoice_document')
                    # print("##############",report)
                    # pdf_content, _ = report._render_qweb_pdf(3)
                    test= self.env['ir.actions.report'].browse(3)
                    print("pdf_content",test)
                    report = self.env['ir.actions.report']._get_report_from_name(
                        'transport_management.report_invoice_document'
                    )
                    report_ref = 'transport_management.report_invoice_document'
                    if not report:
                        raise UserError(_("Report 'transport_management.report_invoice_document' not found"))
                    print("Request Line",request_line)
                    # Generate PDF with proper context
                    pdf_content, _ = report.with_context(
                        active_model='customer.request.line',
                        active_ids=[request_line.id],
                        active_id=request_line.id,
                        lang=self.env.user.lang

                    )._render_qweb_pdf(report.id,res_ids=[request_line.id])
        
                    attachment = self.env['ir.attachment'].create({
                        'name': f'Invoice - {order.name}.pdf',
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': 'customer.request.line',
                        'res_id': request_line.id,
                        'mimetype': 'application/pdf', 
                    })
          
                    mail_values = {
                    'subject': 'Advance Payment Received - Order %s' % order.name,
                    'body_html': (
                        f'<p>Dear {self.customer.name},</p>'
                        f'<p>We are pleased to confirm that we have received your advance payment for order <strong>{order.name}</strong>.</p>'
                        f'<p>Your transaction has been successfully recorded, and we are now proceeding with the next steps of the process.</p>'
                        f'<p><strong>Payment Summary:</strong></p>'
                        f'<table border="1" cellspacing="0" cellpadding="5" style="border-collapse: collapse;">'
                        f'  <tr><th>Order Number</th><td>{order.name}</td></tr>'
                        f'  <tr><th>Invoice</th><td>{self.invoice_id.name}</td></tr>'
                        f'  <tr><th>Amount Received</th><td>{self.amount}</td></tr>'
                        f'  <tr><th>Total Amount</th><td>{self.total_amount}</td></tr>'
                        f'  <tr><th>Payment Date</th><td>{fields.Date.today()}</td></tr>'
                        f'</table>'
                        f'<p>If you have any questions, feel free to reach out to our support team.</p>'
                        f'<p>Thank you for your prompt payment.</p>'
                        f'<p>Best regards,</p>'
                        f'<p>{self.env.company.name}</p>'
                    ),
                    'email_to': self.request_line_id.trader_name.email,
                    'model': 'invoice.wizard',  # Or your actual model
                    'res_id': self.id,
                    'attachment_ids': [(4, attachment.id)],
                    }
                    self.env['mail.mail'].create(mail_values).send()


            elif record.invoice_type == 'final':
                # payment = self.env['account.payment'].search([('move_id', '=', record.invoice_id.id)])
                # payment = self.env['account.payment'].browse(record.payment_id.id)
                # invoice = self.env['account.move'].browse(record.invoice_id.id)
                # #     ('line_ids.move_id', '=', 98),
                # #     ('line_ids.account_id.reconcile', '=', True),  # Only reconcilable accounts
                # #     # ('full_reconcile_id', '=', False),
                # # ])
                # if not payment.move_id or not invoice.exists():
                #     raise UserError("Missing accounting entries")
                
                # payment_line = payment.move_id.line_ids.filtered(
                #     lambda l: l.account_id.account_type == 'asset_receivable'
                #     and not l.reconciled
                # )
                
                # invoice_line = invoice.line_ids.filtered(
                #     lambda l: l.account_id.account_type == 'asset_receivable'
                #     and not l.reconciled
                # )
                # print("payment_line", payment_line)
                # print("invoice_line", invoice_line)
                # # Reconcile
                # if payment_line and invoice_line:
                #     (payment_line + invoice_line).reconcile()
                
                print("payment_line", record.tax_amount,record.amount,record.invoice_id.id)
                return self.invoice_id.lekhaplus_payment_form_button_action()
                # record.request_line_id.state = 'complete'
                # return {
                #     "name": _("Invoice"),
                #     "view_mode": "form",
                #     "res_model": "account.move",
                #     "res_id": record.final_invoice_id.id,
                #     "type": "ir.actions.act_window",
                # }
                
        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'reload',
        #     'params': {'action': 'reload_page'},
        # }
        return {
            "effect": {
                "fadeout": "slow",
                "message": ("Payment Made Successfully"),
                "type": "rainbow_man",
            }
        }
     
