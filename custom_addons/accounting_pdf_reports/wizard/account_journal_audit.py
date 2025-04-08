# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountPrintJournal(models.TransientModel):
    _name = "account.print.journal"
    _inherit = "account.common.journal.report"
    _description = "Account Print Journal"

    sort_selection = fields.Selection([('date', 'Date'), ('move_name', 'Journal Entry Number')],
                                      'Entries Sorted by', required=True, default='move_name')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True,
                                   default=lambda self: self.env['account.journal'].search([('type', 'in', ['sale', 'purchase'])]))

    def _get_report_data(self, data):
        journal_names = [journal.name for journal in self.journal_ids]
        data = self.pre_print_report(data)
        data['form'].update({'sort_selection': self.sort_selection,
                             'fiscal_year_id': self.fiscal_year_id.name,
                             'journal_id_name': journal_names,
                             })
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_journal').with_context(landscape=True).report_action(self, data=data)
