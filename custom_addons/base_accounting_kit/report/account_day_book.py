
import time
from datetime import timedelta, datetime

from odoo import models, api, _
from odoo.exceptions import UserError


class DayBookPdfReport(models.AbstractModel):
    _name = 'report.base_accounting_kit.day_book_report_template'
    _description = 'Day Book Report'

    def _get_account_move_entry(self, accounts, form_data, pass_date):
        # print("=========================date_from_bsdate_from_bs========[[][][]]===================",type(pass_date))
        if isinstance(pass_date, str):
            pass_date = datetime.strptime(pass_date, '%Y-%m-%d').date()  # Adjust format as necessary

        cr = self.env.cr
        move_line = self.env['account.move.line']
        tables, where_clause, where_params = move_line._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        if form_data['target_move'] == 'posted':
            target_move = "AND m.state = 'posted'"
        else:
            target_move = ''
        sql = ('''
                SELECT l.id AS lid, acc.name as accname, l.account_id AS 
                account_id, l.date AS ldate,l.date_bs AS date_bs, j.code AS lcode, l.currency_id, 
                l.amount_currency, l.ref AS lref, l.name AS lname,
                 COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, 
                COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS 
                balance,
                m.name AS move_name, c.symbol AS currency_code, p.name 
                AS partner_name
                FROM account_move_line l
                JOIN account_move m ON (l.move_id=m.id)
                LEFT JOIN res_currency c ON (l.currency_id=c.id)
                LEFT JOIN res_partner p ON (l.partner_id=p.id)
                JOIN account_journal j ON (l.journal_id=j.id)
                JOIN account_account acc ON (l.account_id = acc.id) 
                WHERE l.account_id IN %s AND l.journal_id IN %s '''
               + target_move + ''' AND TO_DATE(l.date_bs, 'YYYY-MM-DD') =  %s
                GROUP BY l.id, l.account_id, l.date_bs,
                     j.code, l.currency_id, l.amount_currency, l.ref, 
                     l.name, m.name, c.symbol, p.name , acc.name
                     ORDER BY l.date_bs DESC
        ''')
        params = (
        tuple(accounts.ids), tuple(form_data['journal_ids']), pass_date)
        cr.execute(sql, params)
        data = cr.dictfetchall()
        res = {}
        debit = credit = balance = 0.00
        for line in data:
            debit += line['debit']
            credit += line['credit']
            balance += line['balance']
         
        res['debit'] = debit
        res['credit'] = credit
        res['balance'] = balance
        res['lines'] = data
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(
            self.env.context.get('active_ids', []))
        form_data = data['form']
        codes = []
        date_from_bs = datetime.strptime(form_data['date_from_bs'], '%Y/%m/%d').date() if form_data.get('date_from_bs') else None
        date_to_bs = datetime.strptime(form_data['date_to_bs'], '%Y/%m/%d').date() if form_data.get('date_to_bs') else None
        
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in
                     self.env['account.journal'].search(
                         [('id', 'in', data['form']['journal_ids'])])]
        active_acc = data['form']['account_ids']
        accounts = self.env['account.account'].search(
            [('id', 'in', active_acc)]) if data['form']['account_ids'] else \
            self.env['account.account'].search([])

        date_start = datetime.strptime(form_data['date_from'],
                                       '%Y-%m-%d').date()
        date_end = datetime.strptime(form_data['date_to'],
                                     '%Y-%m-%d').date()
        days = date_end - date_start
        dates = []
        record = []
        
        for i in range(days.days + 1):
            dates.append(date_from_bs + timedelta(days=i))
        for head in dates:
            pass_date = str(head)
            accounts_res = self.with_context(
                data['form'].get('used_context', {}))._get_account_move_entry(
                accounts, form_data, pass_date)
            # print("=========================================",accounts_res)
            if accounts_res['lines']:
                record.append({
                    'date': head,
                    'debit': accounts_res['debit'],
                    'credit': accounts_res['credit'],
                    'balance': accounts_res['balance'],
                    'child_lines': accounts_res['lines']
                })
        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'date_to_bs': date_to_bs,
            'date_from_bs': date_from_bs,
            'Accounts': record,
            'print_journal': codes,
        }
