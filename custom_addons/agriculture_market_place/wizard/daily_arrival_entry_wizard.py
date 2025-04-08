from datetime import date,datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import nepali_datetime
import json
from urllib.parse import urlencode


class DailyArrivalWizard(models.TransientModel):
    _name = 'daily.arrival.entry'
    _description = 'Daily Arrival Entry Report'

    select_report = fields.Selection([
        ('daily', 'Today'),
        ('weekly', 'This Week'),
        ('monthly','This Month'),
        ('custom', 'Custom'),
        ],
        string='Select Report Type', required=True,
        default='daily')
    report_types = fields.Selection([
        ('vehicle', 'Vehicle'),
        ('commodity', 'Commodity'),
        ('time','Time')
    ], string="Report Specs", required=True, default="commodity")
    more = fields.Boolean(string='Comparable', default=False)
    custom_commodity = fields.Selection([
        ('all', 'All'),
        ('specific', 'Specific'),
        ],
        string='Select Commodity',
        default='all')

    commodity = fields.Many2one('amp.commodity.master', string='Commodity')

    vehicle = fields.Many2many('amp.vehicle.number', string='Vehicle')

    custom_vehicle = fields.Selection([
        ('all', 'All'),
        ('specific', 'Specific'),
        ],
        string='Select Vehicle',
        default='all')

    date_from = fields.Date(string="Start Date")
    date_from_bs = fields.Char(string="Start Date (BS)", compute="_compute_nepali_dates")
    date_to = fields.Date(string="End Date")
    date_to_bs = fields.Char(string="End Date (BS)", compute="_compute_nepali_dates")

    time_from = fields.Char(string="Time From:")
    time_to = fields.Char(string="TIme To:")
    date_for_time = fields.Date(string="Date")
    date_for_time_bs = fields.Date(string="Date",compute="_compute_nepali_dates")

    report_type = fields.Selection([
        ('normal', 'Normal'),
        ('customize', 'Customize')
    ], string='Report Type', required=True, default='normal')

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
            if record.date_for_time:
                nepali_to_date = nepali_datetime.date.from_datetime_date(record.date_for_time)
                record.date_for_time_bs = nepali_to_date.strftime('%Y-%m-%d')
            else:
                record.date_for_time_bs = False

    @api.onchange('more')
    def show_custom_date(self):
        if self.more == False:
            self.report_type = 'normal'
        else:
            self.report_type = 'customize'



    def print_report(self,**kwargs):
        action_type = self.env.context.get('action_type', 'view')  

        print("Action Type:", action_type)
        

        print("More0",self.more)
        if self.more == True:
            domain = []
            domain2 = []
            domain.append(('company_id', '=', self.env.company.id))
            domain2.append(('company_id', '=', self.env.company.id))
            # Create domain for the specific dates
            if self.date_from:
                domain.append(('arrival_date', '=', self.date_from))
            if self.date_to:
                domain2.append(('arrival_date', '=', self.date_to))

            if self.commodity:
                domain.append(('id', '=', self.commodity.id))
                domain2.append(('id', '=', self.commodity.id))
            
            print("print commodity id",self.commodity)
            # Search for records based on the specific dates
            records_from_date = self.env['amp.commodity'].sudo().search(domain)
            records_to_date = self.env['amp.commodity'].sudo().search(domain2)

            # Filter existing records
            existing_records_from = records_from_date.filtered(lambda r: r.exists())
            existing_records_to = records_to_date.filtered(lambda r: r.exists())

            # Aggregate volumes for each date
            commodity_aggregation_from = defaultdict(lambda: {'volume': 0.0, 'unit': None})
            commodity_aggregation_to = defaultdict(lambda: {'volume': 0.0, 'unit': None})

            for record in existing_records_from:
                commodity_aggregation_from[record.name]['volume'] += record.volume
                commodity_aggregation_from[record.name]['unit'] = record.converter.name 
                
            for record in existing_records_to:
                commodity_aggregation_to[record.name]['volume'] += record.volume
                commodity_aggregation_to[record.name]['unit'] = record.converter.name
            # Prepare aggregated data for output
            # aggregated_data_from = [{'name': name, 'volume': data['volume'], 'unit': data['unit']}
            #                         for name, data in commodity_aggregation_from.items()]

            # aggregated_data_to = [{'name': name, 'volume': data['volume'], 'unit': data['unit']}
            #                     for name, data in commodity_aggregation_to.items()
            # if self.date_from:
            #     print(f"Debugging data for {self.date_from}:")
            #     for data in aggregated_data_from:
            #         print("Commodity:", data['name'], "Total Volume:", data['volume'], "Unit:", data['unit'])

            # if self.date_to:
            #     print(f"Debugging data for {self.date_to}:")
            #     for data in aggregated_data_to:
            #         print("Commodity:", data['name'], "Total Volume:", data['volume'], "Unit:", data['unit'])

            all_aggregated_data = [] # List to store aggregated data for all commodities
            for name in set(commodity_aggregation_from.keys()).union(commodity_aggregation_to.keys()): 
                volume_from = commodity_aggregation_from[name]['volume'] 
                volume_to = commodity_aggregation_to[name]['volume'] 
                unit = commodity_aggregation_from[name]['unit'] if volume_from > 0 else commodity_aggregation_to[name]['unit'] 

                change_rate = None 
                change_type = "No Change" 

                # Calculate change_rate handling zero volume_from cases
                if volume_from is not None and volume_to is not None:
                    if volume_from > 0:  
                        # Standard percentage change calculation
                        change_rate = ((volume_to - volume_from) / volume_from) * 100
                        change_type = "Increase" if change_rate > 0 else "Decrease" if change_rate < 0 else "No Change"
                    elif volume_from == 0 and volume_to > 0:
                        # Special case: Volume increased from 0 to a positive value
                        change_rate = 100  # Consider it as a 100% increase from nothing
                        change_type = "Increase"
                    elif volume_from == 0 and volume_to == 0:
                        # No change if both volumes are 0
                        change_rate = 0
                        change_type = "No Change"
                    else:
                        # Decrease from a positive value to zero
                        change_rate = -100
                        change_type = "Decrease"

                all_aggregated_data.append({
                    'name': name, 
                    'from_volume': volume_from, 
                    'to_volume': volume_to, 
                    'unit': unit,
                    'change_rate': change_rate,
                    'change_type': change_type,
                })
            for data in all_aggregated_data:
                print("Commodity:", data['name'], "Total From Volume:", data['from_volume'],"Total To Volume:", data['to_volume'], "Unit:", data['unit'],"change_rate:", data['change_rate'],"%","change_type:",data['change_type'])
         
            if action_type == 'print':
                return {
                    'type': 'ir.actions.report',
                    'report_name': 'agriculture_market_place.daily_arrival_comparable_template',
                    'report_type': 'qweb-pdf',
                    'context': {
                        'report_type': self.select_report,
                        'date_from': self.date_from_bs,
                        'date_to': self.date_to_bs,
                        'all_aggregated_data': all_aggregated_data, 
                        'commodity': self.commodity.product_id.name,
                
                    },
                }
            else:
             
                self.env['temp.commodity.aggregation'].search([]).unlink()
                for data in all_aggregated_data:
                    self.env['temp.commodity.aggregation'].create({
                        'name': data['name'],
                        'from_volume': data['from_volume'],
                        'to_volume': data['to_volume'],
                        'unit': data['unit'],
                        'change_rate': data['change_rate'],
                        'change_types': data['change_type'],
                    })
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'temp.commodity.aggregation',
                    'view_mode': 'tree',
                    'target': 'current',
                    'name' : (f"Comparable Report" ) 
                            #   +(f"Of :{self.commodity.product_id.name}" if self.commodity else '' )
                              +(f"({self.date_from_bs} To {self.date_to_bs})" if self.date_from and self.date_to else ''),
                    'domain': [],
                    'context': {
                        'default_date_from': self.date_from,
                        'default_date_to': self.date_to,
                        'default_report_type': self.select_report,
                        'commodity': self.commodity.product_id.name, 
                        
                    },
                }

        else:
            if self.report_types == 'time':
                print("Report on the basis of Time")
                domain = []
                domain.append(('company_id', '=', self.env.company.id))
            #**************************************************************************** 
                time_from = None
                time_to = None

                # Convert the input time strings to time objects (HH:MM:SS)
                if self.commodity:
                    domain.append(('id', '=', self.commodity.id))

                if self.time_from:
                    # time_from = datetime.strptime(self.time_from, '%H:%M:%S').time()  # Convert to time object
                    time_from = self.time_from 
                if self.time_to:
                    # time_to = fields.Datetime.from_string(self.time_to).time()  # Convert to time object
                    # time_to = datetime.strptime(self.time_to, '%H:%M:%S').time()
                    time_to = self.time_to
                if time_from and time_to:
                    domain.append(('check_in_time', '>=', time_from))  
                    domain.append(('check_in_time', '<=', time_to))  
                elif time_from:
                    domain.append(('check_in_time', '>=', time_from))
                elif time_to:
                    domain.append(('check_in_time', '<=', time_to))

                if self.date_for_time:
                    domain.append(('arrival_date', '=', self.date_for_time))
                else:
                    today = fields.Date.context_today(self)
                    domain.append(('arrival_date', '=', today))

                records = self.env['amp.commodity'].sudo().search(domain)

                existing_records = records.filtered(lambda r: r.exists())
    

                commodity_aggregation = defaultdict(lambda: {'volume': 0.0, 'unit': None})

                for record in existing_records:
                    commodity_aggregation[record.name]['volume'] += record.volume
                    commodity_aggregation[record.name]['unit'] = record.converter.name 
                    commodity_aggregation[record.name]['arrival_date'] = record.arrival_date_bs 
                    # commodity_aggregation[record.name]['final_number'] = record.final_number

                aggregated_data = [{'name': name, 'volume': data['volume'], 'unit': data['unit'], 'arrival_date': data['arrival_date']                    }
                                for name, data in commodity_aggregation.items()]


                for data in aggregated_data:
                    print("Commodity:", data['name'], "Total Volume:", data['volume'], "Unit:", data['unit'])

                if action_type == 'print':
                    return {
                        'type': 'ir.actions.report',
                        'report_name': 'agriculture_market_place.daily_arrival_template',
                        'report_type': 'qweb-pdf',
                        'context': {
                            'report_type': self.select_report,
                            # 'final_number' : False,
                            'time_from': self.time_from,
                            'time_to': self.time_to,
                            'date_for_time': self.date_for_time_bs,
                            'active_ids': existing_records.ids,
                            'aggregated_data': aggregated_data,
                            'commodity': self.commodity.product_id.name,  
                    
                        },
                    }
                else:
                    self.env['temp.commodity.arrival.time'].search([]).unlink()
                    for data in aggregated_data:
                        self.env['temp.commodity.arrival.time'].create({
                            'name': data['name'],
                            'arrival_date': data['arrival_date'],
                            'volume': data['volume'],
                            'unit': data['unit'],
                        })
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'temp.commodity.arrival.time',
                        'view_mode': 'tree',
                        'name': f"Time Basis Report" + 
                        (
                            f"({self.date_for_time})" 
                            if self.date_for_time
                            else ''
                        )+(f"({self.time_from}- {self.time_to})" 
                            if self.time_from and self.time_to
                            else '')
                        ,
                        'target': 'current',
                        'domain': [],
                        'context': {
                            'report_type': self.select_report,
                            # 'final_number' : False,
                            'time_from': self.time_from,
                            'time_to': self.time_to,
                            'date_for_time': self.date_for_time,
                            'commodity': self.commodity.product_id.name, 
                    
                    
                        },
                    }

            else:

                domain = []
                domain.append(('company_id', '=', self.env.company.id))
    
                if self.date_from:
                    domain.append(('arrival_date', '>=', self.date_from))
                if self.date_to:
                    domain.append(('arrival_date', '<=', self.date_to))

                today = fields.Date.context_today(self)
                if self.select_report == 'daily':
                    domain.append(('arrival_date', '=', today))

                elif self.select_report == 'weekly':
                    start_date = today - timedelta(days=today.weekday())
                    end_date = start_date + timedelta(days=6)
                    domain.append(('arrival_date', '>=', start_date))
                    domain.append(('arrival_date', '<=', end_date))

                elif self.select_report == 'monthly':
                    start_date = today.replace(day=1)
                    end_date = (today.replace(day=1) + relativedelta(months=1) - timedelta(days=1))
                    domain.append(('arrival_date', '>=', start_date))
                    domain.append(('arrival_date', '<=', end_date))
                
                if self.commodity:
                    domain.append(('id', '=', self.commodity.id))  

                if self.report_types == 'vehicle':
                    records = self.env['amp.daily.arrival.entry'].sudo().search(domain)
                    for record in records:
                        print("FInasl Nuber",record.final_number)
                    aggregated_data = [{
                        'final_number': record.final_number,
                        'arrival_date_bs':record.arrival_date_bs,
                        'check_in_date_bs':record.check_in_date_bs,
                        'check_out_date_bs':record.check_out_date_bs,
                        'duration':record.duration,
                        } for record in records]
                    if action_type == 'print':
                        return {
                            'type': 'ir.actions.report',
                            'report_name': 'agriculture_market_place.vehicle_duration_template',
                            'report_type': 'qweb-pdf',
                            'context': {
                                'report_type': self.select_report,
                                'date_from': self.date_from_bs,
                                'date_to': self.date_to_bs,
                                'data': aggregated_data,
                                'commodity': self.commodity.product_id.name,
                        
                            },
                        }
                    else:
                        self.env['temp.commodity.arrival.vehicle'].search([]).unlink()
                        for data in aggregated_data:
                            self.env['temp.commodity.arrival.vehicle'].create({
                                'final_number': data['final_number'],
                                'arrival_date': data['arrival_date_bs'],
                                'check_in_date': data['check_in_date_bs'],
                                'check_out_date': data['check_out_date_bs'],
                                'duration': data['duration'],
                            })


                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'temp.commodity.arrival.vehicle',
                            'view_mode': 'tree',
                            'target': 'current',
                            'name': f"Vehicle Basis Report" + 
                            (
                                f"({self.date_from_bs} To {self.date_to_bs})" 
                                if self.date_from and self.date_to 
                                else ''
                            ),
                            'domain': [],
                            'context': {
                                'report_type': self.select_report,
                                'date_from': self.date_from_bs,
                                'date_to': self.date_to_bs,
                                'commodity': self.commodity.product_id.name, 
                            },
                        }
                else:


                    records = self.env['amp.commodity'].sudo().search(domain)
                    existing_records = records.filtered(lambda r: r.exists())
                
                    commodity_aggregation = defaultdict(lambda: {'volume': 0.0, 'unit': None})

                    for record in existing_records:
                        commodity_aggregation[record.name]['volume'] += record.volume
                        commodity_aggregation[record.name]['unit'] = record.converter.name 
                        commodity_aggregation[record.name]['arrival_date'] = record.arrival_date_bs 
                        # commodity_aggregation[record.name]['final_number'] = record.final_number

                    aggregated_data = [{'name': name, 'volume': data['volume'], 'unit': data['unit'], 'arrival_date': data['arrival_date']}
                                    for name, data in commodity_aggregation.items()]


                    for data in aggregated_data:
                        print(" $$$$$$Commodity:", data['name'], "Total Volume:", data['volume'], "Unit:", data['unit'])

                    if action_type == 'print':
                        print("Aggregated Data:", aggregated_data)
                        return {
                            'type': 'ir.actions.report',
                            'report_name': 'agriculture_market_place.daily_arrival_template',
                            'report_type': 'qweb-pdf',
                            'context': {
                                'report_type': self.select_report,
                                'date_from': self.date_from_bs,
                                'date_to': self.date_to_bs,
                                'active_ids': existing_records.ids,
                                'aggregated_data': aggregated_data,  
                        
                            },
                        }
                    else:
                        self.env['temp.commodity.arrival'].search([]).unlink()
                        for data in aggregated_data:
                            self.env['temp.commodity.arrival'].create({
                                'name': data['name'],
                                'arrival_date': data['arrival_date'],
                                'volume': data['volume'], 
                                'unit': data['unit'],
                            })


                        return {
                            'type': 'ir.actions.act_window', 
                            'res_model': 'temp.commodity.arrival',
                            'view_mode': 'tree',
                            'target': 'current',
                            'name' : f"Report Type :({self.select_report.upper()}) Arrival Report",
                            # 'view_id':'view_temp_commodity_arrival_tree',
                            'domain': [],
                            'context': {
                                'report_type': self.select_report,
                                'date_from': self.date_from_bs,
                                'date_to': self.date_to_bs,
                                'commodity': self.commodity.product_id.name, 
                            },
                        }