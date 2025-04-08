from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
from collections import defaultdict
from odoo import http
import json
import nepali_datetime

class DailyPriceWizard(models.TransientModel):
    _name = 'amp.daily.price.wizard'
    _description = 'Daily Price Report Wizard'

    date_from = fields.Date(string="From Date")
    date_from_bs = fields.Char(string="From Date (BS)", compute="_compute_nepali_dates")
    date_to = fields.Date(string="To Date")
    date_to_bs = fields.Char(string="To Date (BS)", compute="_compute_nepali_dates")
    current_date = fields.Date(string="Current Date")
    current_date_bs = fields.Char(string="Current Date (BS)", compute="_compute_current_date_bs")
    more = fields.Boolean(string='More Options')
    report_range = fields.Selection([
        ('today', 'Today'),
        ('this_week', 'This Week'),
        ('this_month', 'This Month'),
        ('custom', 'Custom')
    ], string='Report Range', required=True, default='today')
    report_type = fields.Selection([
        ('normal', 'Normal'),
        ('comparison', 'Comparison')
    ], string='Report Type', required=True, default='normal')
    is_all_commodities = fields.Boolean(string='All Commodities', default = True)
    commodity = fields.Many2one(comodel_name='amp.commodity.master', string='Commodity')
    comparison_commodity = fields.Many2one(comodel_name='amp.commodity.master', string='Comparison Commodity')
    # target_date = fields.Date(string='Target Date', required=True)
    
    @api.depends('current_date')
    def _compute_current_date_bs(self):
        for record in self:
            if record.current_date:
                nepali_date = nepali_datetime.date.from_datetime_date(record.current_date)
                record.current_date_bs = nepali_date.strftime('%Y-%m-%d')
            else:
                record.current_date_bs = False

    @api.depends('date_from', 'date_to')
    def _compute_nepali_dates(self):
        for record in self:
            if record.date_from:
                nepali_from_date = nepali_datetime.date.from_datetime_date(record.date_from)
                record.date_from_bs = nepali_from_date.strftime('%Y-%m-%d')
            else:
                record.date_from_bs = False

            if record.date_to:
                nepali_to_date = nepali_datetime.date.from_datetime_date(record.date_to)
                record.date_to_bs = nepali_to_date.strftime('%Y-%m-%d')
            else:
                record.date_to_bs = False


    @api.onchange('report_type')
    def change_report_range(self):
        if self.report_type == 'comparison':
            self.report_range = 'custom'

    def print_report(self):
        action_type = self.env.context.get('action_type', 'view')
        today = fields.Date.context_today(self)
        if self.report_range != 'custom':
            domain = []
            domain.append(('company_id', '=', self.env.company.id))
            if self.report_range == 'today':
                domain = [('current_date', '=', today)]
                date_from = date_to = today
            elif self.report_range == 'this_week':
                date_to = today
                date_from = date_to - timedelta(days=6)
                domain = [('current_date', '>=', date_from), ('current_date', '<=', date_to)]
            elif self.report_range == 'this_month':
                date_to = today
                date_from = date_to - timedelta(days=30)
                domain = [('current_date', '>=', date_from), ('current_date', '<=', date_to)]
            if self.commodity:
                domain.append(('commodity', '=', self.commodity.id)) 

            records = self.env['amp.daily.price'].search(domain)
            
            latest_records = {}

            for record in records:
                key = (record.commodity.id, record.current_date)
                # Only store if this is the first occurrence or if it's later than the stored one
                if key not in latest_records or record.write_date > latest_records[key].write_date:
                    latest_records[key] = record

            daily_price_data = [
                {
                    'id': record.id,
                    'unit': record.unit.name,
                    'commodity_id': record.commodity.product_id.name,
                    'current_date': record.current_date_bs,
                    'min_price': round(record.min_price, 2),
                    'max_price': round(record.max_price, 2),
                    'avg_price': round(record.avg_price, 2),
                }
                for record in latest_records.values()
            ]



            # For debugging purposes
            formatted_records = pformat(daily_price_data, indent=4)
            print(formatted_records)

            if action_type == 'print':
                return {
                    'type': 'ir.actions.report',
                    'report_name': 'agriculture_market_place.report_daily_price',
                    'report_type': 'qweb-pdf',
                    'context': {
                        'date_from': self.date_from_bs,
                        'date_to': self.date_to_bs,
                        'daily_price_report': daily_price_data,
                        'report_type': self.report_range,
                        'commodity': self.commodity.product_id.name,
                    },
                }
            else:
                self.env['temp.commodity.price'].search([]).unlink()
                for data in daily_price_data:
                    self.env['temp.commodity.price'].create({
                        'name': data['commodity_id'],
                        'unit': data['unit'],
                        'arrival_date': data['current_date'],
                        'maximum': data['max_price'],
                        'minimum': data['min_price'],
                        'avg_price': data['avg_price'],
                    })


                return {
                    
                    'type': 'ir.actions.act_window', 
                    'res_model': 'temp.commodity.price',
                    'view_mode': 'tree',
                    'target': 'current',
                    'name': ( f"{dict(self._fields['report_range'].selection).get(self.report_range, '')}"  if self.report_range else '')
                        + f"Report"
                        + (f" Of {self.commodity.product_id.name}" if self.commodity else '')
                        + (f" {self.date_from_bs} To {self.date_to_bs}" 
                        if self.date_from and self.date_to 
                        else ''
                    ),
                    # 'view_id':'view_temp_commodity_arrival_tree',
                    'domain': [],
                    'context': {
                        'report_type': self.report_type,
                        'date_from': self.date_from_bs,
                        'date_to': self.date_to_bs,
                
                    },
                }

        else:
            domain = []
            domain.append(('company_id', '=', self.env.company.id))
            if self.report_type == 'normal':
                print(f"Current date in report type normal {self.current_date_bs}")
                if not self.date_from or not self.date_to:
                    raise UserError(_('Please specify both From Date and To Date.'))
                from_date = self.date_from
                to_date = self.date_to
                domain = [('current_date', '>=', from_date), ('current_date', '<=', to_date)]

                if self.commodity:
                    domain.append(('commodity', '=', self.commodity.id)) 
                records = self.env['amp.daily.price'].search(domain)

                formatted_records = pformat(records.mapped(lambda r: {
                    'id': r.id,
                    'commodity_id': r.commodity.product_id.name,
                    'current_date': r.current_date,
                    }), indent=4)
                print("Fetched Records:\n", formatted_records)
                latest_records = {}
                for record in records:
                    key = (record.commodity.id, record.current_date)
                    # Only store if this is the first occurrence or if it's later than the stored one
                    if key not in latest_records or record.write_date > latest_records[key].write_date:
                        latest_records[key] = record

                daily_price_data = [{
                    'id': record.id,
                    'unit': record.unit.name,
                    'commodity_id': record.commodity.product_id.name,
                    'current_date': record.current_date_bs,
                    'min_price': round(record.min_price, 2),
                    'max_price': round(record.max_price, 2),
                    'avg_price': round(record.avg_price, 2),
                }for record in latest_records.values()
                ]
                if action_type == 'print':
                    return {
                        'type': 'ir.actions.report',
                        'report_name': 'agriculture_market_place.report_daily_price',
                        'report_type': 'qweb-pdf',
                        'context': {
                            'date_from': self.date_from,
                            'date_to': self.date_to,
                            'daily_price_report': daily_price_data,
                            'report_type': self.report_range,
                            'commodity': self.commodity.product_id.name,
                        },
                    }
                else:
                    self.env['temp.commodity.normal'].search([]).unlink()
                    for data in daily_price_data:
                        self.env['temp.commodity.normal'].create({
                            'name': data['commodity_id'],
                            'unit': data['unit'],
                            'arrival_date': data['current_date'],
                            'maximum': data['max_price'],
                            'minimum': data['min_price'],
                            'avg_price': data['avg_price'],
                        })


                return {
                    'type': 'ir.actions.act_window', 
                    'res_model': 'temp.commodity.normal',
                    'view_mode': 'tree',
                    'target': 'current',
                    'name': (f"Price Report")
                        + (f" Of {self.commodity.product_id.name}" if self.commodity else '')
                        + (f"{self.date_from_bs} To {self.date_to_bs}" 
                        if self.date_from and self.date_to 
                        else ''
                    ),
                    # 'view_id':'view_temp_commodity_arrival_tree',
                    'domain': [],
                    'context': {
                        'report_type': self.report_type,
                        'date_from': self.date_from_bs,
                        'date_to': self.date_to_bs,
                
                    },
                }

                # context = {
                #     'date_from': self.date_from.strftime('%Y-%m-%d') if self.date_from else None,
                #     'date_to': self.date_to.strftime('%Y-%m-%d') if self.date_to else None,
                #     'daily_price_report': daily_price_data,
                # }

                # # Generate the report URL with parameters
                # report_data_encoded = http.url_encode({'report_data': json.dumps(context)})
                # report_url = f"/report/view_daily_price_report?{report_data_encoded}"

                # return {
                #     'type': 'ir.actions.act_url',
                #     'url': report_url,
                #     'target': 'new',  # Open in a new tab
                # }

            else:
                # print(" +++COmparisonCOmparisonCOmparisonCOmparison ===============================")
                domain = []
                domain2 = []
                domain.append(('company_id', '=', self.env.company.id))
                domain2.append(('company_id', '=', self.env.company.id))
                if not self.date_from or not self.date_to:
                    raise UserError(_('Please specify both From Date and To Date.'))
                
                domain.append(('current_date', '=', self.date_from))
                domain2.append(('current_date', '=', self.date_to))

                if self.commodity:
                    domain.append(('commodity', '=', self.commodity.id))
                    domain2.append(('commodity', '=', self.commodity.id))
                
                print("print commodity id",self.commodity)
                
     
                
                records_from_date = self.env['amp.daily.price'].sudo().search(domain)
                records_to_date = self.env['amp.daily.price'].sudo().search(domain2)

                def aggregate_latest(records):
                    aggregated_data = defaultdict(lambda: {
                        'max_price': 0,
                        'min_price': float('inf'),
                        'total_avg': 0,
                        'count': 0,
                        'name': None,
                        'unit': None
                    })

                    for record in records:
                        commodity_id = record.commodity.id
                        commodity_name = record.commodity.product_id.name
                        commodity_unit = record.commodity.unit.name

              
                        aggregated_data[commodity_id]['max_price'] = max(aggregated_data[commodity_id]['max_price'], record.max_price)
                        aggregated_data[commodity_id]['min_price'] = min(aggregated_data[commodity_id]['min_price'], record.min_price)
                        aggregated_data[commodity_id]['total_avg'] += record.avg_price
                        aggregated_data[commodity_id]['count'] += 1
                        
            
                        aggregated_data[commodity_id]['name'] = commodity_name
                        aggregated_data[commodity_id]['unit'] = commodity_unit

               
                    for commodity_id, data in aggregated_data.items():
                        data['avg_price'] = data['total_avg'] / data['count'] if data['count'] > 0 else 0

                    return aggregated_data

                aggregated_from = aggregate_latest(records_from_date)
                aggregated_to = aggregate_latest(records_to_date)
                print("Aggregated From Date Records:")
                for commodity_id, data in aggregated_from.items():
                    commodity_name = self.env['amp.commodity.master'].browse(commodity_id).product_id.name
                    print(f"Commodity ID: {commodity_id}")
                    print(f"Commodity Name {commodity_name}")
                    print(f"Unit: {data['unit']}")
                    print(f"  Max Price: {data['max_price']}")
                    print(f"  Min Price: {data['min_price']}")
                    print(f"  Average Price: {data['avg_price']}")
                    print()

                print("Aggregated To Date Records:")
                for commodity_id, data in aggregated_to.items():
                    commodity_name = self.env['amp.commodity.master'].browse(commodity_id).product_id.name
                    print(f"Commodity ID: {commodity_id}")
                    print(f"Unit: {data['unit']}")
                    print(f"Commodity Name {commodity_name}")
                    print(f"  Max Price: {data['max_price']}")
                    print(f"  Average Price: {data['avg_price']}")
                    print()

            comparison_report = []

            for commodity_id in set(aggregated_from.keys()).union(aggregated_to.keys()):
                from_data = aggregated_from.get(commodity_id, {})
                to_data = aggregated_to.get(commodity_id, {})
                
                entry = {
                        'name': from_data.get('name') or to_data.get('name'),
                        'unit': from_data.get('unit') or to_data.get('unit'),
                        'from_data': {
                            'max_price': round(from_data.get('max_price', 0), 2) if 'max_price' in from_data else None,
                            'min_price': round(from_data.get('min_price', 0), 2) if 'min_price' in from_data else None,
                            'avg_price': round(from_data.get('avg_price', 0), 2) if 'avg_price' in from_data else None,
                        },
                        'to_data': {
                            'max_price': round(to_data.get('max_price', 0), 2) if 'max_price' in to_data else None,
                            'min_price': round(to_data.get('min_price', 0), 2) if 'min_price' in to_data else None,
                            'avg_price': round(to_data.get('avg_price', 0), 2) if 'avg_price' in to_data else None,
                        },
                        'change_rate': {}
                    }

                
                # Calculate change rates if there is data for both dates
                if from_data and to_data:
                    for metric in ['max_price', 'min_price', 'avg_price']:
                        from_value = from_data.get(metric)
                        to_value = to_data.get(metric)
                        if from_value and from_value > 0:  # Avoid division by zero
                            change_rate = ((to_value - from_value) / from_value) * 100
                            # entry['change_rate'][metric] = round(change_rate, 2)
                            change_status = 'increase' if change_rate > 0 else 'decrease' if change_rate < 0 else 'no change'
            
                            # Append the change rate and the status ('increase', 'decrease', or 'no change')
                            entry['change_rate'][metric] = {
                                'value': round(change_rate, 2),
                                'status': change_status
                            }
    
                comparison_report.append(entry)
          

            if action_type == 'print':
                return {
                    'type': 'ir.actions.report',
                    'report_name': 'agriculture_market_place.report_comparable_daily_price',
                    'report_type': 'qweb-pdf',
                    'context': {
                        'date_from': self.date_from_bs,
                        'date_to': self.date_to_bs,
                        'comparison_report': comparison_report,
                        'report_type': self.report_range,
                        'commodity': self.commodity.product_id.name,
                    },
                }
            else:
                self.env['temp.commodity.compare'].search([]).unlink()
            
                for data in comparison_report:
                    self.env['temp.commodity.compare'].create({
                        'name': data['name'],
                        'unit': data['unit'],
                        'date_from': self.date_from_bs,
                        'date_to': self.date_to_bs,
                        'avg_price_from': data['from_data'].get('avg_price'),
                        'avg_price_to': data['to_data'].get('avg_price'),
                        # 'change_rate_avg_price': data['change_rate'].get('avg_price'),
                        'change_rate_avg_price': data['change_rate'].get('avg_price', {}).get('value'),
                        'change_rate_avg_price_status': data['change_rate'].get('avg_price', {}).get('status'),
                    })


            return {
                'type': 'ir.actions.act_window', 
                'res_model': 'temp.commodity.compare',
                'view_mode': 'tree',
                'target': 'current',
                'name':(f" Comparison Report")
                        + (f" Of {self.commodity.product_id.name}" if self.commodity else '')
                        + (f"{self.date_from_bs} To {self.date_to_bs}" 
                        if self.date_from and self.date_to 
                        else ''
                    ),
                # 'view_id':'view_temp_commodity_arrival_tree',
                'domain': [],
                'context': {
                    'report_type': self.report_type,
                    'date_from': self.date_from_bs,
                    'date_to': self.date_to_bs,
            
                },
            }