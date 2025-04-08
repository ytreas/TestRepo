
from odoo import fields, models


class AccountPartnerLedger(models.TransientModel):
    _name = "account.report.partner.ledger"
    _inherit = "account.common.partner.report"
    _description = "Account Partner Ledger"

    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_report_partner_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_report_partner_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    vendor_selection = fields.Many2one('res.partner', string="Vendors", domain="[('supplier_rank', '>', 0)]")
    name = fields.Char(string="Partner Ledger Report",
                       default="Partner Ledger Report", required=True,
                       translate=True)
    amount_currency = fields.Boolean("With Currency",
                                     help="It adds the currency column on"
                                          " report if the "
                                          "currency differs from the "
                                          "company currency.")
    reconciled = fields.Boolean(string='Reconciled Entries')

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled,
                             'amount_currency': self.amount_currency})
        return self.env.ref(
            'base_accounting_kit.action_report_partnerledger').report_action(
            self, data=data)
