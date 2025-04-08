
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError

class SalesTeam(models.Model):
    _inherit = "crm.team"
    name_np = fields.Char(string="Name in Nepali")
#1234

class AccountJournal(models.Model):
    """Module inherited for adding the reconcile method in the account
    journal"""
    _inherit = "account.journal"
    name_np = fields.Char(string="Name in Nepali")

    def action_open_reconcile(self):
        """Function to open reconciliation view for bank statements
        belonging to this journal"""
        if self.type in ['bank', 'cash']:
            # Open reconciliation view for bank statements belonging
            # to this journal
            bank_stmt = self.env['account.bank.statement'].search(
                [('journal_id', 'in', self.ids)]).mapped('line_ids')
            return {
                'type': 'ir.actions.client',
                'tag': 'bank_statement_reconciliation_view',
                'context': {'statement_line_ids': bank_stmt.ids,
                            'company_ids': self.mapped('company_id').ids},
            }
        else:
            # Open reconciliation view for customers/suppliers
            action_context = {'show_mode_selector': False,
                              'company_ids': self.mapped('company_id').ids}
            if self.type == 'sale':
                action_context.update({'mode': 'customers'})
            elif self.type == 'purchase':
                action_context.update({'mode': 'suppliers'})
            return {
                'type': 'ir.actions.client',
                'tag': 'manual_reconciliation_view',
                'context': action_context,
            }

    def create_cash_statement(self):
        """for redirecting in to bank statement lines"""
        return {
            'name': _("Statements"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,form',
            'context': {'default_journal_id': self.id},
        }
