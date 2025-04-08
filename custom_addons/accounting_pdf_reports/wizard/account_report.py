# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from datetime import datetime

class AccountingReport(models.TransientModel):
    _name = "accounting.report"
    _inherit = "account.common.report"
    _description = "Accounting Report"

    @api.model
    def _get_account_report(self):
        reports = []
        if self._context.get('active_id'):
            menu = self.env['ir.ui.menu'].browse(self._context.get('active_id')).name
            reports = self.env['account.financial.report'].search([('name', 'ilike', menu)])
        return reports and reports[0] or False

    enable_filter = fields.Boolean(string='Enable Comparison')
    account_report_id = fields.Many2one('account.financial.report', string='Account Reports',
                                        required=True, default=_get_account_report)
    label_filter = fields.Char(string='Column Label', help="This label will be displayed on report to "
                                                           "show the balance computed for the given comparison filter.")
    filter_cmp = fields.Selection([('filter_no', 'No Filters'), ('filter_date', 'Date')],
                                  string='Filter by', required=True, default='filter_no')
    date_from_cmp = fields.Date(string='Date From')
    date_from_cmp_bs = fields.Char(string='Date From')
    date_to_cmp = fields.Date(string='Date To')
    date_to_cmp_bs = fields.Date(string='Date To')
    debit_credit = fields.Boolean(string='Display Debit/Credit Columns',
                                  help="This option allows you to get more details about "
                                       "the way your balances are computed."
                                       " Because it is space consuming, we do not allow to"
                                       " use it while doing a comparison.")

    def _build_comparison_context(self, data):
        result = {}
        result['fiscal_year_id'] = 'fiscal_year_id' in data['form'] and data['form']['fiscal_year_id'] or False
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        if data['form']['filter_cmp'] == 'filter_date':
            result['date_from'] = data['form']['date_from_cmp']
            result['date_to'] = data['form']['date_to_cmp']
            result['strict_range'] = True
        return result

    def check_report(self):
        res = super(AccountingReport, self).check_report()
        data = {}
        data['form'] = self.read(['account_report_id', 'date_from_cmp', 'date_to_cmp', 'journal_ids', 'filter_cmp', 'target_move'])[0]
        for field in ['account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(data)
        res['data']['form']['comparison_context'] = comparison_context
        return res

    def _print_report(self, data):
        data['form'].update(self.read(['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter', 'target_move'])[0])
        return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(self, data=data, config=False)
    
    @api.onchange('fiscal_year_id')
    def _onchange_fiscal_year(self):
        bs_date_from_str = self.fiscal_year_id.date_from_bs
        bs_date_to_str = self.fiscal_year_id.date_to_bs
        
        if not bs_date_from_str or not bs_date_to_str:
            return
        
        try:
            bs_date_from = datetime.strptime(bs_date_from_str, '%Y/%m/%d')
            bs_date_to = datetime.strptime(bs_date_to_str, '%Y/%m/%d')
            
            print("bs_date_from:", bs_date_from)
            bs_to_ad_difference = relativedelta(years=56, months=8, days=15)  # 8.5 months is approximately 8 months and 15 days
            
            print("bs_to_ad_difference:", bs_to_ad_difference)
            
            ad_date_from = bs_date_from - bs_to_ad_difference
            ad_date_to = bs_date_to - bs_to_ad_difference
            
            self.date_from = ad_date_from.strftime('%Y-%m-%d')
            self.date_to = ad_date_to.strftime('%Y-%m-%d')
            print("abc",self.date_from, self.date_to)
            
        except ValueError as e:
            print("Error parsing dates:", e)
