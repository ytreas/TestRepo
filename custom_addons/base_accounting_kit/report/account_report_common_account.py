

from odoo import api, fields, models
from odoo.tools.misc import get_lang


class AccountCommonAccountReport(models.TransientModel):
    _name = 'account.common.account.report'
    _description = 'Account Common Account Report'
    _inherit = "account.report"

    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_common_report_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_common_report_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    display_account = fields.Selection(
        [('all', 'All'), ('movement', 'With movements'),
         ('not_zero', 'With balance is not equal to 0')],
        string='Display Accounts', required=True, default='movement')
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True,
                                   default='posted')
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    date_from_bs = fields.Date(string='Start Date BS', store=True)
    date_to_bs = fields.Date(string='End Date BS', store=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True,
                                 readonly=True,
                                 default=lambda self: self.env.company)

    def _build_contexts(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form'][
            'journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form'][
            'target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        result['company_id'] = data['form']['company_id'][0] or False
        return result

    def _print_report(self, data):
        raise NotImplementedError()

    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(
            ['date_from', 'date_to', 'journal_ids', 'target_move',
             'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context,
                                            lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report(data)

    def pre_print_report(self, data):
        data['form'].update(self.read(['display_account'])[0])
        return data
