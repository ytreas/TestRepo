
import time
from dateutil.relativedelta import relativedelta
from odoo import api, models, _
from odoo.exceptions import UserError,ValidationError
from datetime import datetime
import nepali_datetime
from odoo.tools import float_is_zero
import nepali_datetime
from collections import defaultdict



class ReportAgedPartnerBalance(models.AbstractModel):
    _name = 'report.base_accounting_kit.report_agedpartnerbalance'
    _description = 'Aged Partner Balance Report'

    def _get_partner_move_lines(self, account_type, date_from, target_move, period_length):
        MoveLine = self.env['account.move.line']
        domain = [
            ('account_id.account_type', '=', account_type),
            ('parent_state', '=', target_move),
            # ('reconciled', '=', False),
            ('move_id.state', '=', 'posted'),
            ('move_id.payment_state', 'in', ['not_paid', 'partial'])
        ]
        if 'asset_receivable' in account_type:
            domain.append(('move_id.move_type', '=', 'out_invoice'))
        elif 'liability_payable' in account_type:
            domain.append(('move_id.move_type', '=', 'in_invoice'))
        move_lines = MoveLine.search(domain)

        partners = {}
        totals = {
            '0': 0.0,
            '1': 0.0,
            '2': 0.0,
            '3': 0.0,
            '4': 0.0,
            'total': 0.0,
        }
        lines_dict = defaultdict(list)

        for line in move_lines:
            partner = line.partner_id
            if not partner.ref_company_ids:
                continue
            partner_id = partner.id
            due_date = line.date
            amount = abs(line.amount_residual)
            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            else:
                date_from = date_from
            age_days = (date_from - due_date).days
            if age_days < 0:
                continue  # skip not-yet-due lines

            if partner_id not in partners:
                partners[partner_id] = {
                    'direction': 0.0,
                    '0': 0.0,
                    '1': 0.0,
                    '2': 0.0,
                    '3': 0.0,
                    '4': 0.0,
                    'total': 0.0,
                    'partner_id': partner_id,
                    'name': partner.name,
                    'trust': partner.trust,
                }
            partner_data = partners[partner_id]

            bucket = (age_days // period_length) + 1
            print("age_days", age_days)
            print("period_length", period_length)
            print("bucket", bucket)
            if bucket > 4:
                bucket = 4
            bucket_key = str(bucket)
            if bucket_key == '4':
                bucket_key = '0'
            elif bucket_key == '3':
                bucket_key = '1'
            elif bucket_key == '2':
                bucket_key = '2'
            elif bucket_key == '1':
                bucket_key = '3'
            elif bucket_key == '0':
                bucket_key = '4'
            partner_data[bucket_key] += amount
            partner_data['total'] += amount

            totals[bucket_key] += amount
            totals['total'] += amount

            lines_dict[partner_id].append(line.id)

        print("lines_dict", lines_dict)
        res = list(partners.values())
        total_list = [
            totals['0'],
            totals['1'],
            totals['2'],
            totals['3'],
            totals['4'],
            totals['total'],
            0.0
        ]
        lines = {pid: lines_dict.get(pid, []) for pid in partners.keys()}

        print("res", res)
        print("total", total_list)
        print("lines", lines)
        return res, total_list, lines

    @api.model
    def _get_report_values(self, docids, data=None):
        print("data in get_report_values", data)
        if not data.get('form') or not self.env.context.get(
                'active_model') or not self.env.context.get('active_id'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        target_move = data['form'].get('target_move', 'all')
        date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))
        if data['form']['result_selection'] == 'customer':
            account_type = ['asset_receivable']
        elif data['form']['result_selection'] == 'supplier':
            account_type = ['liability_payable']
        else:
            account_type = ['liability_payable', 'asset_receivable']
        movelines, total, dummy = self._get_partner_move_lines(account_type,
                                                               date_from,
                                                               target_move,
                                                               data['form']
                                                               ['period_length']
                                                               )
        try:
            if isinstance(date_from, str):
                ad_date_from_date = datetime.strptime(data['form']['date_from'], "%Y-%m-%d").date()
            else:
                ad_date_from_date = data['form']['date_from']
            from_bs_date = nepali_datetime.date.from_datetime_date(ad_date_from_date)
            
            data['form']['date_from']=from_bs_date
        except Exception as e:
            raise ValidationError(_("Invalid Date Type provided."))
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_partner_lines': movelines,
            'get_direction': total,
        }
