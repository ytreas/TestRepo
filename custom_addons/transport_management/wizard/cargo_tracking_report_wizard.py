from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.transport_order import convert_to_bs_date
from datetime import datetime, timedelta
import nepali_datetime
from nepali_datetime import date as nepali_date
from pytz import timezone

class CargoTrackingReport(models.TransientModel):
    _name = 'cargo.tracking.report.wizard'
    _description = 'Cargo Tracking Report'

    FILTERS = [
        ('date', 'Date Range'),
    ]

    # Filter Fields
    filter_by = fields.Selection(FILTERS, string="Filter By", required=True, default='date')
    date_from = fields.Date(string="From Date", store=True) 
    date_to = fields.Date(string="To Date", store=True)
    date_from_bs = fields.Char(string="From Date (BS)", compute='_compute_bs_date', store=True)
    date_to_bs = fields.Char(string="To Date (BS)", compute='_compute_bs_date', store=True)

    # Tree View Fields
    tracking_no = fields.Char(string='Tracking Number', readonly=True)
    origin = fields.Char(string='Origin', readonly=True)
    destination = fields.Char(string='Destination', readonly=True)
    status = fields.Char(string='Status', readonly=True)
    dispatch_datetime = fields.Datetime(string='Dispatch Date', readonly=True)
    delivery_datetime = fields.Datetime(string='Delivery Date', readonly=True)
    last_updated = fields.Char(string='Last Updated', readonly=True)
    mode_of_transport = fields.Char(string='Transport Mode', readonly=True)
    checkpoint_count = fields.Integer(string='Checkpoints', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_("From Date cannot be after To Date."))

    @api.constrains('date_from', 'date_to')
    def _check_future_dates(self):
        today = fields.Date.today()
        for record in self:
            if record.date_from and record.date_from > today:
                raise UserError(_("Start date cannot be in the future."))
            if record.date_to and record.date_to > today:
                raise UserError(_("End date cannot be in the future."))
            
    @api.depends('date_from', 'date_to')
    def _compute_bs_date(self):
        for rec in self:
            rec.date_from_bs = convert_to_bs_date(rec.date_from) if rec.date_from else ''
            rec.date_to_bs = convert_to_bs_date(rec.date_to) if rec.date_to else ''

    def get_tracking_data(self):
        print("Date from and date to", self.date_from, self.date_to)

        duty_domain = [
            ('duty_allocation_date', '>=', self.date_from),
            ('duty_allocation_date', '<=', self.date_to),
            ('state', 'in', ['confirmed', 'in_transit', 'delivered'])
        ]
        
        duties = self.env['duty.allocation'].search(duty_domain, order='duty_allocation_date')
        print('Duties found:', len(duties))

        data = []
        for duty in duties:
            order_domain = [
                ('name', '=', duty.transport_order),
                ('scheduled_date_to', '>=', self.date_from),
                ('scheduled_date_to', '<=', self.date_to),
                ('state', '!=', 'draft')
            ]
            
            order = self.env['transport.order'].search(order_domain, limit=1)
            print('Order found:', order)
            if not order:
                continue
            
            utc_dt = fields.Datetime.from_string(order.write_date)
            kathmandu_tz = timezone('Asia/Kathmandu')
            local_dt = utc_dt.replace(tzinfo=timezone('UTC')).astimezone(kathmandu_tz)
            local_date = local_dt.date()
            local_time = local_dt.strftime('%H:%M:%S')
            bs_date = convert_to_bs_date(local_date)

            checkpoint_details = []
            for checkpoint in duty.checkpoints:
                if checkpoint.reached:
                    checkpoint_details.append({
                        'transit_name': checkpoint.name.name,
                        'transit_time': checkpoint.reached_at,
                        'transit_status': 'Transit Reached',
                        'transit_remarks': checkpoint.remarks or '',
                    })

            shipment_details = {
                'tracking_no': order.tracking_number,
                'origin': order.pickup_address or _('N/A'),
                'destination': order.delivery_address or _('N/A'),
                'status': dict(order._fields['state'].selection).get(order.state),
                'last_updated': f"{bs_date} {local_time}",
                'dispatch_datetime': duty.start_datetime,
                'dispatch_remarks': 'Left sorting facility',
                'delivery_datetime': duty.delivery_datetime,
                'delivery_remarks': 'Signed by receiver',
                'checkpoint_details': checkpoint_details,
                'mode_of_transport': 'Road',
                'checkpoint_count': len(checkpoint_details)
            }
            data.append(shipment_details)
        print('Data prepared for report:', data)
        return data

    def view_tracking(self):
        self.ensure_one()
        
        # Get tracking data first
        tracking_data = self.get_tracking_data()
        
        if not tracking_data:
            raise UserError(_("No records found for the selected date range."))

        # Clear old records
        old_records = self.search([
            ('create_uid', '=', self.env.uid),
            ('id', '!=', self.id)
        ])
        if old_records:
            old_records.unlink()

        # Create new records
        records_to_create = []
        for shipment in tracking_data:
            vals = {
                'tracking_no': shipment['tracking_no'] or False,
                'origin': shipment['origin'],
                'destination': shipment['destination'],
                'status': shipment['status'],
                'dispatch_datetime': shipment['dispatch_datetime'],
                'delivery_datetime': shipment['delivery_datetime'],
                'last_updated': shipment['last_updated'],
                'mode_of_transport': shipment['mode_of_transport'],
                'checkpoint_count': shipment['checkpoint_count']
            }
            records_to_create.append(vals)

        # Bulk create new records
        new_records = self.create(records_to_create)

        # Return action to show tree view only
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cargo Tracking Results'),
            'res_model': self._name,
            'view_mode': 'tree',
            'view_id': self.env.ref('transport_management.view_cargo_tracking_tree').id,
            'target': 'current',
            'domain': [('id', 'in', new_records.ids)],
        }
    
    def print_report(self):
        self.ensure_one()
        tracking_data = self.get_tracking_data()
        
        if not tracking_data:
            raise UserError(_("No records found for the selected date range."))

        return {
            'type': 'ir.actions.report',
            'report_name': 'transport_management.cargo_report_template',
            'report_type': 'qweb-pdf',
            'data': {
                'date_from': self.date_from_bs,
                'date_to': self.date_to_bs,
                'today_date': convert_to_bs_date(fields.Date.today()),
                'company_name': self.env.company.name,
                'report_name': 'Cargo Tracking Report',
                'prepared_data': tracking_data,
            }
        }