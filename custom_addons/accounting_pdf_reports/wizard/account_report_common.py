# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import get_lang
import datetime
import functools
import io
import itertools
import json
import logging
import operator
from collections import OrderedDict


from werkzeug.exceptions import InternalServerError

import odoo
import odoo.modules.registry
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
from odoo.http import content_disposition, request
from odoo.tools import lazy_property, osutil, pycompat
from odoo.tools.misc import xlsxwriter
from odoo.tools.translate import _
from odoo.addons.web.controllers.export import ExcelExport
import jwt
from datetime import datetime
from dateutil.relativedelta import relativedelta


class AccountCommonReport(models.TransientModel):
    _name = "account.common.report"
    _description = "Account Common Report"

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        string='Journals',
        required=True,
        default=lambda self: self.env['account.journal'].search([('company_id', '=', self.company_id.id)]),
        domain="[('company_id', '=', company_id)]",
    )
    fiscal_year_id = fields.Many2one('account.fiscal.year',string='Fiscal Year')
    date_from = fields.Date(string='Start Date')
    date_from_bs = fields.Char(string='Start Date')
    date_to = fields.Date(string='End Date')
    date_to_bs = fields.Char(string='End Date')
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')
    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.journal_ids = self.env['account.journal'].search(
                [('company_id', '=', self.company_id.id)])
        else:
            self.journal_ids = self.env['account.journal'].search([])

    def _build_contexts(self, data):
        result = {}
        result['fiscal_year_id'] = 'fiscal_year_id' in data['form'] and data['form']['fiscal_year_id'] or False
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
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
        data['form'] = self.read(['fiscal_year_id','date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        print("------------------------------>here")
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report(data)

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
            
        except ValueError as e:
            print("Error parsing dates:", e)

    def get_transient_model_fields(self):
        transient_model_fields = []
        fields_view = self.env['account.move.line'].fields_get()
        if self._name=="account.report.partner.ledger":
            if fields_view:
                if self.amount_currency:
                    print("currency")
                    selected_fields = [
                        'date', 'date_range_fy_id',
                        'account_id', 'balance','partner_id','currency_id'
                    ]
                else:
                    print("uncurrency")
                    selected_fields = [
                        'date', 'date_range_fy_id',
                        'account_id', 'balance','partner_id'
                    ]
                selected_fields = [
                    'date', 'date_range_fy_id',
                    'account_id', 'balance','partner_id'
                ]
        elif self._name=="account.print.journal":
            if fields_view:
                selected_fields = [
                    'date', 'date_range_fy_id','journal_id', 
                    'account_id', 'balance','partner_id','credit','debit'
                ]
        elif self._name=="account.report.general.ledger":
            if fields_view:
                selected_fields = [
                    'date', 'journal_id', 'partner_id', 'date_range_fy_id',
                    'account_id', 'balance','move_id','debit','credit', 'currency_id'
                ]
        elif self._name=="account.balance.report":
            if fields_view:
                selected_fields = [
                    'journal_id', 'partner_id', 'date_range_fy_id',
                    'account_id', 'account_id.code', 'balance','move_id','debit','credit', 'currency_id'
                ]
        else:
            if fields_view:
                if self.account_report_id.name=="Balance Sheet":
                    if self.debit_credit:
                        selected_fields = [
                            'date', 'date_range_fy_id',
                            'account_id', 'balance','debit','credit'
                        ]
                    else:
                        selected_fields = [
                            'date', 'date_range_fy_id',
                            'account_id', 'balance'
                        ]
                elif self.account_report_id.name=="Profit and Loss":
                    if self.debit_credit:
                        selected_fields = [
                            'date', 'date_range_fy_id',
                            'account_id', 'balance','debit','credit'
                        ]
                    else:
                        selected_fields = [
                            'date', 'date_range_fy_id',
                            'account_id', 'balance'
                        ]
                else:
                    selected_fields = [
                        'date', 'date_range_fy_id', 'company_id', 'journal_id', 'move_name',
                        'account_id', 'partner_id', 'ref', 'product_id', 'name', 'tax_ids',
                        'amount_currency', 'currency_id', 'debit', 'credit', 'tax_tag_ids',
                        'discount_date', 'discount_amount_currency', 'tax_line_id',
                        'date_maturity', 'balance', 'matching_number', 'amount_residual',
                        'amount_residual_currency', 'analytic_distribution'
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
            'domain': [
                ('date_range_fy_id.name', '=', self.fiscal_year_id.name),
            ],
            'fields': fields_trans,
            'groupby': ['journal_id'],
            'ids': False,
            'model': 'account.move.line',
            'report_model': self._name,
        }
        if self._name == "account.report.partner.ledger":
            name=[]
            for partner in self.partner_ids:
                name.append(partner.name)
            if self.reconciled:
                if self.result_selection == 'supplier':
                    export_data['domain'] = [('date_range_fy_id.name', '=', self.fiscal_year_id.name),(('partner_id.name', '=', name)),(('account_id.reconcile', '=', True)),'|', ('account_id.name', '=', 'Account Payable'), ('account_id.name', '=', 'Tax Payable')]
                elif self.result_selection == 'customer':
                    export_data['domain'] = [('date_range_fy_id.name', '=', self.fiscal_year_id.name),(('partner_id.name', '=', name)),(('account_id.reconcile', '=', True)),'|','|', ('account_id.name', '=', 'Account Receivable (PoS)'), ('account_id.name', '=', 'Account Receivable'), ('account_id.name', '=', 'Tax Receivable')]
                elif self.result_selection == 'customer_supplier':
                    export_data['domain'] = [('date_range_fy_id.name', '=', self.fiscal_year_id.name),(('partner_id.name', '=', name)),(('account_id.reconcile', '=', True)),'|','|','|','|', ('account_id.name', '=', 'Account Receivable (PoS)'), ('account_id.name', '=', 'Account Receivable'), ('account_id.name', '=', 'Tax Receivable'),('account_id.name', '=', 'Account Payable'), ('account_id.name', '=', 'Tax Payable')]                
            else:
                if self.result_selection == 'supplier':
                    export_data['domain'] = [('date_range_fy_id.name', '=', self.fiscal_year_id.name),(('partner_id.name', '=', name)),(('account_id.reconcile', '=', False)),'|', ('account_id.name', '=', 'Account Payable'), ('account_id.name', '=', 'Tax Payable')]
                elif self.result_selection == 'customer':
                    export_data['domain'] = [('date_range_fy_id.name', '=', self.fiscal_year_id.name),(('partner_id.name', '=', name)),(('account_id.reconcile', '=', False)),'|','|', ('account_id.name', '=', 'Account Receivable (PoS)'), ('account_id.name', '=', 'Account Receivable'), ('account_id.name', '=', 'Tax Receivable')]
                elif self.result_selection == 'customer_supplier':
                    export_data['domain'] = [('date_range_fy_id.name', '=', self.fiscal_year_id.name),(('partner_id.name', '=', name)),(('account_id.reconcile', '=', False)),'|','|','|','|', ('account_id.name', '=', 'Account Receivable (PoS)'), ('account_id.name', '=', 'Account Receivable'), ('account_id.name', '=', 'Tax Receivable'),('account_id.name', '=', 'Account Payable'), ('account_id.name', '=', 'Tax Payable')]
        elif self._name == "account.report.general.ledger":
            journals=[]
            accounts=[]
            partners=[]
            for account in self.account_ids:
                accounts.append(account.name)
            for journal in self.journal_ids:
                journals.append(journal.name)
            for partner in self.partner_ids:
                partners.append(partner.name)
            export_data['domain'].append(('journal_id.name', '=', journals))
            export_data['domain'].append(('account_id.name', '=', accounts))
            export_data['domain'].append(('partner_id.name', '=', partners))
            if self.sortby == 'sort_date':
                export_data['groupby']: ['date']
        elif self._name == "account.balance.report":
            name=[]
            journals=[]
            for journal in self.journal_ids:
             journals.append(journal.name)
            export_data['domain'].append(('journal_id.name', '=', journals))
        elif self._name == "account.print.journal":
            export_data['groupby']: ['journal_id']
            journals=[]
            for journal in self.journal_ids:
                journals.append(journal.name)
            export_data['domain'].append(('journal_id.name', '=', journals))
        elif self._name == "accounting.report":
            if self.account_report_id.name=="Profit and Loss":
                        export_data['domain'] = [
                                                    ('date_range_fy_id.name', '=', self.fiscal_year_id.name),
                                                    '|',
                                                    '|', 
                                                    ('account_id.account_type', '=', "income"),
                                                    ('account_id.account_type', '=', "income_others"),
                                                    ('account_id.account_type', '=', "expense"),
                                                ]
        return self.perform_export(export_data)