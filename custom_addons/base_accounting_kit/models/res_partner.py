from datetime import date, timedelta
from odoo import fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"

    invoice_list = fields.One2many('account.move',
                                   'partner_id',
                                   string="Invoice Details",
                                   readonly=True,
                                   domain=(
                                   [('payment_state', '=', 'not_paid'),
                                    ('move_type', '=', 'out_invoice')]))
    total_due = fields.Monetary(compute='_compute_for_followup', store=False,
                                readonly=True)
    next_reminder_date = fields.Date(compute='_compute_for_followup',
                                     store=False, readonly=True)
    next_reminder_date_bs = fields.Char()
    total_overdue = fields.Monetary(compute='_compute_for_followup',
                                    store=False, readonly=True)
    followup_status = fields.Selection(
        [('in_need_of_action', 'In need of action'),
         ('with_overdue_invoices', 'With overdue invoices'),
         ('no_action_needed', 'No action needed')],
        string='Followup status',
        )
    name_np = fields.Char(string="Name(Np):")
    pan_no  = fields.Char(string="Pan Number:")
    verification_status=fields.Boolean('Verification Status',default=True)
    registration_no=fields.Char('Registration Number')
    student_id=fields.Integer('Student ID')
    
    def _compute_for_followup(self):
        """
        Compute the fields 'total_due', 'total_overdue' ,
        'next_reminder_date' and 'followup_status'
        """
        for record in self:
            total_due = 0
            total_overdue = 0
            today = fields.Date.today()
            for am in record.invoice_list:
                if am.company_id == self.env.company:
                    amount = am.amount_residual
                    total_due += amount

                    is_overdue = today > am.invoice_date_due \
                        if am.invoice_date_due else today > am.date
                    if is_overdue:
                        total_overdue += amount or 0
            min_date = record.get_min_date()
            action = record.action_after()
            if min_date:
                date_reminder = min_date + timedelta(days=action)
                if date_reminder:
                    record.next_reminder_date = date_reminder
            else:
                date_reminder = today
                record.next_reminder_date = date_reminder
            if total_overdue > 0 and date_reminder > today:
                followup_status = "with_overdue_invoices"
            elif total_due > 0 and date_reminder <= today:
                followup_status = "in_need_of_action"
            else:
                followup_status = "no_action_needed"
            record.total_due = total_due
            record.total_overdue = total_overdue
            record.followup_status = followup_status

    def get_min_date(self):
        today = date.today()
        for this in self:
            if this.invoice_list:
                min_list = this.invoice_list.mapped('invoice_date_due')
                while False in min_list:
                    min_list.remove(False)
                return min(min_list)
            else:
                return today

    def get_delay(self):
        delay = """SELECT fl.id, fl.delay
                    FROM followup_line fl
                    JOIN account_followup af ON fl.followup_id = af.id
                    WHERE af.company_id = %s
                    ORDER BY fl.delay;

                    """
        self._cr.execute(delay, [self.env.company.id])
        record = self._cr.dictfetchall()
        return record


    def action_after(self):
        lines = self.env['followup.line'].search([(
            'followup_id.company_id', '=', self.env.company.id)])
        if lines:
            record = self.get_delay()
            for i in record:
                return i['delay']
