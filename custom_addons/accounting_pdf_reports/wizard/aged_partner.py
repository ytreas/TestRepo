# -*- coding: utf-8 -*-

import time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.web.controllers.export import ExcelExport
import jwt

class AccountAgedTrialBalance(models.TransientModel):
    _name = 'account.aged.trial.balance'
    _inherit = 'account.common.partner.report'
    _description = 'Account Aged Trial balance Report'

    period_length = fields.Integer(string='Period Length (days)', required=True, default=30)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)
    date_from = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))
    date_from_bs = fields.Char(string='Start Date',store=True)

    def _get_report_data(self, data):
        res = {}
        data = self.pre_print_report(data)
        data['form'].update(self.read(['period_length'])[0])
        period_length = data['form']['period_length']
        if period_length <= 0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not data['form']['date_from_bs']:
            raise UserError(_('You must set a start date.'))
        start = data['form']['date_from_bs']
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            res[str(i)] = {
                'name': (i != 0 and (str((5 - (i + 1)) * period_length) + '-' + str((5 - i) * period_length)) or (
                            '+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        data['form'].update(res)
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_aged_partner_balance').\
            with_context(landscape=True).report_action(self, data=data)


    def get_transient_model_fields(self):
        transient_model_fields = []
        fields_view = self.env['account.move.line'].fields_get()
        if fields_view:
            selected_fields = [
                'date',
                'account_id', 'balance'
            ]
        for field_name, field_attrs in fields_view.items():
            if field_name in selected_fields:
                f = {
                    'name': field_name,
                    'label': field_attrs.get('string', field_name),
                    'store': True,  # You may adjust this based on your requirements
                    'type': field_attrs.get('type', 'char'),  # Default to 'char' if type is not available
                }
                transient_model_fields.append(f)

        return transient_model_fields

    def perform_export(self, export_data):
        jwt_data = jwt.encode({
            'data': export_data
        }, 'secret', algorithm="HS256")
        return {
            'type': 'ir.actions.act_url',
            'name': "Export Url",
            'url': f'/export_report?data={jwt_data}',
            'target': self,
        }
    
    def on_export_click(self):
        fields_trans = self.get_transient_model_fields()
        export_data = {
            'import_compat': False,
            'context': {
                'journal_type': self.env.context.get('journal_type', 'general'),
                'lang': self.env.context.get('lang', 'en_US'),
                'tz': self.env.context.get('tz', 'UTC'),
                'uid': self.env.context.get('uid', False),
                'allowed_company_ids': self.env.context.get('allowed_company_ids', []),
            },
            'fields': fields_trans,
            'groupby': ['account_id'],
            'ids': False,
            'model': 'account.move.line',
            'report_model': self._name,
        }
        formatted_date = self.date_from.isoformat()
        export_data['domain'] = [
            ('date', '>=', formatted_date),
        ]
        name=[]
        for partner in self.partner_ids:
            name.append(partner.name)
            export_data['domain'].append(('partner_id.name', '=', name))
        return self.perform_export(export_data)