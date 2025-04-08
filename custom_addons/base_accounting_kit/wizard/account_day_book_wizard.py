
from datetime import date
from odoo import fields, models


class DayBookWizard(models.TransientModel):
    _name = 'account.day.book.report'
    _description = 'Account Day Book Report'

    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True,
                                 default=lambda self: self.env.company)
    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   required=True,
                                   default=lambda self: self.env[
                                       'account.journal'].search([]))
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')],
                                   string='Target Moves', required=True,
                                   default='posted')
    account_ids = fields.Many2many('account.account',
                                   'account_report_daybook_account_rel',
                                   'report_id', 'account_id',
                                   'Accounts')
    date_from = fields.Date(string='Start Date', 
                            required=True)
    
    date_to = fields.Date(string='End Date',
                          required=True)
    date_from_bs = fields.Char(string='Start Date BS',store=True)
    date_to_bs = fields.Char(string='End Date BS',store=True)

    def _build_contexts(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form'][
            'journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form'][
            'target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False

        result['date_from_bs'] = data['form']['date_from_bs'] or False
        result['date_to_bs'] = data['form']['date_to_bs'] or False
        
        result['strict_range'] = True if result['date_from'] else False
        return result

    def check_report(self):
        self.ensure_one()

        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = \
        self.read(['date_from', 'date_to','date_from_bs','date_to_bs', 'journal_ids', 'target_move',
                   'account_ids'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context,
                                            lang=self.env.context.get(
                                                'lang') or 'en_US')

        return self.env.ref(
            'base_accounting_kit.day_book_pdf_report').report_action(self,
                                                                     data=data)
