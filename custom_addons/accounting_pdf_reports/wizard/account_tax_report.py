# -*- coding: utf-8 -*-

from odoo import models, api, fields
from datetime import date
from odoo.addons.web.controllers.export import ExcelExport
import jwt


class AccountTaxReport(models.TransientModel):
    _name = 'account.tax.report.wizard'
    _inherit = "account.common.report"
    _description = 'Tax Report'

    # date_from = fields.Date(string='Date From', required=True,
    #                         default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    # date_to = fields.Date(string='Date To', required=True,
    #                       default=lambda self: fields.Date.to_string(date.today()))

    def _print_report(self, data):
        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data=data)


    def get_transient_model_fields(self):
        transient_model_fields = []
        fields_view = self.env['account.move.line'].fields_get()
        if fields_view:
            selected_fields = [
                'date', 'date_range_fy_id',
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
            'groupby': [],
            'ids': False,
            'model': 'account.move.line',
        }
        export_data['domain'] = [
            ('date_range_fy_id.name', '=', self.fiscal_year_id.name),
            '|',
            '|', 
                ('account_id.code', '=', '131000'),
                ('account_id.code', '=', '132000'),
                ('account_id.code', '=', '251000'),
        ]
        return self.perform_export(export_data)