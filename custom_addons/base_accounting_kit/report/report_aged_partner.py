
import time
from dateutil.relativedelta import relativedelta
from odoo import api, models, _
from odoo.exceptions import UserError,ValidationError
from datetime import datetime
import nepali_datetime
from odoo.tools import float_is_zero



class ReportAgedPartnerBalance(models.AbstractModel):
    _name = 'report.base_accounting_kit.report_agedpartnerbalance'
    _description = 'Aged Partner Balance Report'

    def _get_partner_move_lines(self, account_type, date_from, target_move, period_length):
        # This method can receive the context key 'include_nullified_amount' {Boolean}
        # Do an invoice and a payment and unreconcile. The amount will be nullified
        # By default, the partner wouldn't appear in this report.
        # The context key allow it to appear
        # In case of a period_length of 30 days as of 2019-02-08,
        # we want the following periods:
        # Name       Stop         Start
        # 1 - 30   : 2019-02-07 - 2019-01-09
        # 31 - 60  : 2019-01-08 - 2018-12-10
        # 61 - 90  : 2018-12-09 - 2018-11-10
        # 91 - 120 : 2018-11-09 - 2018-10-11
        # +120     : 2018-10-10
        
        # Calculate the periods
        periods = {}
        if isinstance(date_from, str):
            start = datetime.strptime(date_from, "%Y-%m-%d")
        else:
            start = date_from
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            
        # Set up the periods based on period_length
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length)
            period_name = str((5 - (i + 1)) * period_length + 1) + '-' + str((5 - i) * period_length)
            period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
            if i == 0:
                period_name = '+' + str(4 * period_length)
            periods[str(i)] = {
                'name': period_name,
                'stop': period_stop,
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop
            
        # Initialize results and totals
        res = []
        total = []
        cr = self.env.cr
        user_company = self.env.company
        user_currency = user_company.currency_id
        ResCurrency = self.env['res.currency'].with_context(date=date_from)
        company_ids = self._context.get('company_ids') or [user_company.id]
        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']
            
        # Initialize totals
        for i in range(7):
            total.append(0)
            
        # Build the reconciliation clause
        reconciliation_clause = '(l.reconciled IS FALSE)'
        cr.execute(
            'SELECT debit_move_id, credit_move_id FROM account_partial_reconcile'
            ' where max_date > %s',
            (date_from,))
        reconciled_after_date = []
        for row in cr.fetchall():
            reconciled_after_date += [row[0], row[1]]
            
        if reconciled_after_date:
            reconciliation_clause = '(l.reconciled IS FALSE OR l.id IN %s)'
            arg_list = (tuple(move_state), tuple(account_type), tuple(reconciled_after_date))
        else:
            arg_list = (tuple(move_state), tuple(account_type))
            
        # Add common parameters to query
        arg_list += (date_from, tuple(company_ids))
        
        # Query to get partners with move lines
        query = '''
            SELECT DISTINCT l.partner_id, UPPER(res_partner.name::text)
            FROM account_move_line AS l left join res_partner on l.partner_id = res_partner.id, 
                 account_account, account_move am
            WHERE (l.account_id = account_account.id)
                AND (l.move_id = am.id)
                AND (am.state IN %s)
                AND (account_account.account_type IN %s)
                AND ''' + reconciliation_clause + '''
                AND (l.date <= %s)
                AND l.company_id IN %s
            ORDER BY UPPER(res_partner.name::text)'''
            
        cr.execute(query, arg_list)
        partners = cr.dictfetchall()
        
        # Build a string like (1,2,3) for easy use in SQL query
        partner_ids = [partner['partner_id'] for partner in partners if partner['partner_id']]
        lines = dict((partner['partner_id'] or False, []) for partner in partners)
        
        if not partner_ids:
            return [], [], {}
            
        # Get undue amounts (amounts not yet due)
        undue_amounts = {}
        query = '''SELECT l.id
                FROM account_move_line AS l, account_account, account_move am
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (account_account.account_type IN %s)
                    AND (COALESCE(l.date_maturity,l.date) >= %s)\
                    AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                AND (l.date <= %s)
                AND l.company_id IN %s'''
                
        cr.execute(query, (
            tuple(move_state), tuple(account_type), date_from,
            tuple(partner_ids), date_from, tuple(company_ids)))
            
        aml_ids = cr.fetchall()
        aml_ids = aml_ids and [x[0] for x in aml_ids] or []
        
        # Process undue amounts
        for line in self.env['account.move.line'].browse(aml_ids):
            partner_id = line.partner_id.id or False
            if partner_id not in undue_amounts:
                undue_amounts[partner_id] = 0.0
                
            line_amount = ResCurrency._get_conversion_rate(
                line.company_id.currency_id, user_currency, line.balance)
                
            if user_currency.is_zero(line_amount):
                continue
                
            # Process matched debits
            for partial_line in line.matched_debit_ids:
                if partial_line.max_date <= date_from:
                    line_amount += ResCurrency._get_conversion_rate(
                        partial_line.company_id.currency_id, user_currency,
                        partial_line.amount)
                        
            # Process matched credits
            for partial_line in line.matched_credit_ids:
                if partial_line.max_date <= date_from:
                    line_amount -= ResCurrency._get_conversion_rate(
                        partial_line.company_id.currency_id, user_currency,
                        partial_line.amount)
                        
            if not self.env.company.currency_id.is_zero(line_amount):
                undue_amounts[partner_id] += line_amount
                lines[partner_id].append({
                    'line': line,
                    'amount': line_amount,
                    'period': 6,
                })
                
        # Use one query per period and store results in history
        history = []
        for i in range(5):
            args_list = (tuple(move_state), tuple(account_type), tuple(partner_ids),)
            dates_query = '(COALESCE(l.date_maturity,l.date)'

            # Adjust query based on period start/stop
            if periods[str(i)]['start'] and periods[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (periods[str(i)]['start'], periods[str(i)]['stop'])
            elif periods[str(i)]['start']:
                dates_query += ' >= %s)'
                args_list += (periods[str(i)]['start'],)
            else:
                dates_query += ' <= %s)'
                args_list += (periods[str(i)]['stop'],)
                
            args_list += (date_from, tuple(company_ids))
            
            # Query for this period
            query = '''SELECT l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.account_type IN %s)
                        AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                        AND ''' + dates_query + '''
                    AND (l.date <= %s)
                    AND l.company_id IN %s'''
                    
            cr.execute(query, args_list)
            partners_amount = {}
            aml_ids = cr.fetchall()
            aml_ids = aml_ids and [x[0] for x in aml_ids] or []
            
            # Process each move line for this period
            for line in self.env['account.move.line'].browse(aml_ids):
                partner_id = line.partner_id.id or False
                if partner_id not in partners_amount:
                    partners_amount[partner_id] = 0.0
                    
                line_amount = ResCurrency._get_conversion_rate(
                    line.company_id.currency_id, user_currency, line.balance)
                    
                if user_currency.is_zero(line_amount):
                    continue
                    
                # Process matched debits for this line
                for partial_line in line.matched_debit_ids:
                    if partial_line.max_date <= date_from:
                        line_amount += ResCurrency._get_conversion_rate(
                            partial_line.company_id.currency_id, user_currency,
                            partial_line.amount)
                            
                # Process matched credits for this line
                for partial_line in line.matched_credit_ids:
                    if partial_line.max_date <= date_from:
                        line_amount -= ResCurrency._get_conversion_rate(
                            partial_line.company_id.currency_id, user_currency,
                            partial_line.amount)
                            
                if not self.env.company.currency_id.is_zero(line_amount):
                    partners_amount[partner_id] += line_amount
                    lines[partner_id].append({
                        'line': line,
                        'amount': line_amount,
                        'period': i + 1,
                    })
                    
            history.append(partners_amount)
            
        # Process partners to prepare final result
        for partner in partners:
            if partner['partner_id'] is None:
                partner['partner_id'] = False
                
            at_least_one_amount = False
            values = {}
            undue_amt = 0.0
            
            # Get undue amount for this partner
            if partner['partner_id'] in undue_amounts:
                undue_amt = undue_amounts[partner['partner_id']]
                
            # Add to total
            total[6] = total[6] + undue_amt
            values['direction'] = undue_amt
            
            # Check if partner has any amounts
            if not float_is_zero(values['direction'], 
                             precision_rounding=self.env.company.currency_id.rounding):
                at_least_one_amount = True
                
            # Process each period for this partner
            for i in range(5):
                during = False
                if partner['partner_id'] in history[i]:
                    during = [history[i][partner['partner_id']]]
                    
                # Add to total for this period
                total[i] = total[i] + (during and during[0] or 0)
                values[str(i)] = during and during[0] or 0.0
                
                if not float_is_zero(values[str(i)],
                                 precision_rounding=self.env.company.currency_id.rounding):
                    at_least_one_amount = True
                    
            # Calculate total for this partner
            values['total'] = sum([values['direction']] + [values[str(i)] for i in range(5)])
            
            # Add to overall total
            total[5] += values['total']
            values['partner_id'] = partner['partner_id']
            
            # Get partner info
            if partner['partner_id']:
                browsed_partner = self.env['res.partner'].browse(partner['partner_id'])
                values['name'] = browsed_partner.name and len(browsed_partner.name) >= 45 and \
                            browsed_partner.name[0:40] + '...' or browsed_partner.name
                values['trust'] = browsed_partner.trust
            else:
                values['name'] = _('Unknown Partner')
                values['trust'] = False
                
            # Add to results if partner has amounts or lines
            if at_least_one_amount or (self._context.get('include_nullified_amount') and 
                                    lines[partner['partner_id']]):
                res.append(values)
                
        return res, total, lines

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        This function prepares the report data while maintaining the same return structure
        """
        if not data.get('form') or not self.env.context.get('active_model') or not self.env.context.get('active_id'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
            
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        
        # Get parameters from the data form
        target_move = data['form'].get('target_move', 'all')
        date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))
        period_length = data['form'].get('period_length', 30)
        
        # Determine account type based on selected result type
        if data['form']['result_selection'] == 'customer':
            account_type = ['asset_receivable']
        elif data['form']['result_selection'] == 'supplier':
            account_type = ['liability_payable']
        else:
            account_type = ['liability_payable', 'asset_receivable']
            
        # Get the move lines data using same logic as the API
        movelines, total, dummy = self._get_partner_move_lines(
            account_type, date_from, target_move, period_length
        )
        
        # Convert date to Nepali if needed
        try:
            if isinstance(date_from, str):
                ad_date_from_date = datetime.strptime(data['form']['date_from'], "%Y-%m-%d").date()
            else:
                ad_date_from_date = data['form']['date_from']
                
            from_bs_date = nepali_datetime.date.from_datetime_date(ad_date_from_date)
            data['form']['date_from'] = from_bs_date
        except Exception as e:
            raise ValidationError(_("Invalid Date Type provided."))
            
        # Return data in the same format as original function
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_partner_lines': movelines,
            'get_direction': total,
        }
