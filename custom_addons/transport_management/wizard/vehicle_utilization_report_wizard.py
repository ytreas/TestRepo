from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.transport_order import convert_to_bs_date
from datetime import datetime, timedelta
import io
import base64
import xlsxwriter

class VehicleUtilizationReport(models.TransientModel):
    _name = 'vehicle.utilization.report.wizard'
    _description = 'Vehicle Utilization Report'

    FILTERS = [
        ('date', 'Date Range'),
        ('vehicle', 'Vehicle'),
        ('vehicle_type', 'Vehicle Type'),
        ('utilization', 'Utilization Range'),
        ('both', 'Both Date Range and Vehicle'),
    ]

    UTILIZATION_RANGES = [
        ('low', 'Low (0-50%)'),
        ('medium', 'Medium (51-80%)'),
        ('high', 'High (>80%)'),
    ]

    VEHICLE_SYSTEM = [
        ('old', 'Old Vehicle System'),
        ('new', 'New Vehicle System'),
        ('pradesh', 'Pradesh Vehicle System')
    ]

    # Base Fields
    filter_by = fields.Selection(FILTERS, string="Filter By", required=True, default='date')
    date_from = fields.Date(string="From Date", store=True)
    date_to = fields.Date(string="To Date", store=True)
    date_from_bs = fields.Char(string="From Date (BS)", compute='_compute_bs_date', store=True)
    date_to_bs = fields.Char(string="To Date (BS)", compute='_compute_bs_date', store=True)
    vehicle_id = fields.Many2one('vehicle.number', string='Vehicle')
    vehicle_system = fields.Selection(VEHICLE_SYSTEM, string='Vehicle System', default='old')
    utilization_range = fields.Selection(UTILIZATION_RANGES, string='Utilization Range')

    # Vehicle Type Fields
    old_vehicle_type = fields.Many2one('custom.vehicle.type', string='Vehicle Type (Old)')
    two_wheeler = fields.Selection([
        ('motorcycle', 'Motorcycle'),
        ('scooter', 'Scooter'),
        ('moped', 'Moped'), 
        ('e_rickshaw', 'E-Rickshaw'),
    ], string="2 Wheeler")

    four_wheeler = fields.Selection([
        ('car', 'Car'),
        ('jeep', 'Jeep'),
        ('cargo_van', 'Cargo/Delivery Van'),
    ], string="4 Wheeler")

    heavy = fields.Selection([
        ('tempo', 'Tempo'),
        ('power_tiller', 'Power Tiller'),
        ('tractor', 'Tractor'),
        ('minibus', 'Minibus'),
        ('mini_truck', 'Mini Truck'),
        ('truck', 'Truck'),
        ('bus', 'Bus'),
        ('lorry', 'Lorry'),
        ('road_roller', 'Road Roller'),
        ('dozer', 'Dozer'),
        ('crane', 'Crane'),
        ('fire_brigade', 'Fire Brigade'),
        ('loader', 'Loader'),
        ('excavator', 'Excavator'),
        ('backhoe_loader', 'Backhoe Loader'),
        ('grader', 'Grader'),
        ('forklift', 'Forklift'),
        ('other_heavy_equipment', 'Other Heavy Equipment'),
    ], string="Heavy Vehicle")

    @api.onchange('filter_by')
    def _onchange_filter_by(self):
        """Reset fields when filter changes"""
        self.ensure_one()
        vals = {
            'date_from': False,
            'date_to': False,
            'vehicle_id': False,
            # 'vehicle_system': False,
            'old_vehicle_type': False,
            'two_wheeler': False,
            'four_wheeler': False,
            'heavy': False,
            'utilization_range': False,
        }
        if self.filter_by in ['date', 'both']:
            vals.update({
                'date_from': fields.Date.today(),
                'date_to': fields.Date.today()
            })
        self.update(vals)
    
    @api.onchange('two_wheeler', 'four_wheeler', 'heavy')
    def _onchange_vehicle_types(self):
        """Make vehicle type fields mutually exclusive"""
        self.ensure_one()
        if self.two_wheeler:
            self.four_wheeler = False
            self.heavy = False
        elif self.four_wheeler:
            self.two_wheeler = False
            self.heavy = False
        elif self.heavy:
            self.two_wheeler = False
            self.four_wheeler = False

    @api.constrains('two_wheeler', 'four_wheeler', 'heavy')
    def _check_vehicle_types(self):
        """Ensure only one vehicle type is selected"""
        for record in self:
            selected_types = [
                record.two_wheeler, 
                record.four_wheeler, 
                record.heavy
            ].count(bool)
            if selected_types > 1:
                raise UserError(_("Please select only one type of vehicle"))
        
    @api.onchange('vehicle_system')
    def _onchange_vehicle_system(self):
        self.ensure_one()
        # Clear all vehicle type fields
        self.old_vehicle_type = False
        self.two_wheeler = False
        self.four_wheeler = False
        self.heavy = False

    @api.constrains('date_from', 'date_to', 'filter_by')
    def _check_date_range(self):
        for record in self:
            if record.filter_by in ['date', 'both']:
                if not record.date_from or not record.date_to:
                    raise UserError(_("Please select both From and To dates"))
                if record.date_from > record.date_to:
                    raise UserError(_("Start date must be before end date"))

    @api.constrains('date_from', 'date_to')
    def _check_future_dates(self):
        today = fields.Date.today()
        for record in self:
            if record.date_from and record.date_from > today:
                raise UserError(_("Start date cannot be in the future."))
            if record.date_to and record.date_to > today:
                raise UserError(_("End date cannot be in the future."))

    @api.constrains('vehicle_id', 'old_vehicle_type', 'utilization_range', 'filter_by', 'vehicle_system', 'two_wheeler', 'four_wheeler', 'heavy')
    def _check_filter_requirements(self):
        for record in self:
            if record.filter_by in ['vehicle', 'both'] and not record.vehicle_id:
                raise UserError(_("Please select a vehicle"))
                
            if record.filter_by == 'vehicle_type':
                if not record.vehicle_system:
                    raise UserError(_("Please select a vehicle system"))
                
                if record.vehicle_system == 'old' and not record.old_vehicle_type:
                    raise UserError(_("Please select a vehicle type for old system"))
                    
                if record.vehicle_system == 'new':
                    if not any([record.two_wheeler, record.four_wheeler, record.heavy]):
                        raise UserError(_("Please select a vehicle type for new system"))
                        
            if record.filter_by == 'utilization' and not record.utilization_range:
                raise UserError(_("Please select a utilization range"))

    @api.depends('date_from', 'date_to')
    def _compute_bs_date(self):
        for rec in self:
            rec.date_from_bs = convert_to_bs_date(rec.date_from) if rec.date_from else ''
            rec.date_to_bs = convert_to_bs_date(rec.date_to) if rec.date_to else ''

    def _get_vehicle_data(self):
        """Get vehicle utilization data grouped by date."""
        # Get today's date if no date range is specified
        today = fields.Date.today()
        
        # Build date list
        date_list = []
        if self.filter_by in ['date', 'both']:
            current_date = self.date_from
            while current_date <= self.date_to:
                date_list.append(current_date)
                current_date += timedelta(days=1)
        else:
            # For vehicle filter, get last 100 days by default
            for i in range(100):
                date_list.append(today - timedelta(days=i))
            date_list.reverse()

        # Get vehicles based on filter
        domain = []
        if self.filter_by in ['vehicle', 'both']:
            domain += [('id', '=', self.vehicle_id.id)]
        if self.filter_by == 'vehicle_type':
            if self.vehicle_system == 'old' and self.old_vehicle_type:
                domain = [
                    ('vehicle_type', '=', self.old_vehicle_type.id),
                    ('vehicle_system', '=', 'old')
                ]
            elif self.vehicle_system == 'pradesh' and self.old_vehicle_type:
                domain = [
                    ('vehicle_type', '=', self.old_vehicle_type.id),
                    ('vehicle_system', '=', 'pradesh')
                ]
            elif self.vehicle_system == 'new':
                if self.two_wheeler:
                    domain = [
                        ('two_wheeler', '=', self.two_wheeler),
                        ('vehicle_system', '=', 'new')
                    ]
                elif self.four_wheeler:
                    domain = [
                        ('four_wheeler', '=', self.four_wheeler),
                        ('vehicle_system', '=', 'new')
                    ]
                elif self.heavy:
                    domain = [
                        ('heavy', '=', self.heavy),
                        ('vehicle_system', '=', 'new')
                    ]

        vehicles = self.env['vehicle.number'].search(domain)

        if not vehicles:
            raise UserError(_("No vehicles found for the selected criteria."))

        daily_data = []
        
        for current_date in date_list:
            next_date = current_date + timedelta(days=1)
            
            for vehicle in vehicles:
                # Build assignment domain with date filter
                assignment_domain = [
                    ('vehicle_id', '=', vehicle.id),
                    ('order_id.state', '=', 'delivered'),
                    ('assigned_date', '>=', current_date),
                    ('assigned_date', '<', next_date)
                ]

                assignments = self.env['transport.assignment'].search(assignment_domain)

                if assignments:
                    trips_count = len(assignments)
                    load_capacity = vehicle.volume or 0.0

                    # Calculate total and average used capacity
                    total_used_capacity = sum(assignment.order_id.cargo_weight for assignment in assignments)
                    avg_used_capacity = total_used_capacity / trips_count
                    
                    # Calculate utilization based on average used capacity
                    utilization = (avg_used_capacity / load_capacity * 100) if load_capacity > 0 else 0.0

                    # Determine vehicle type
                    vehicle_type = ''
                    if vehicle.vehicle_system == 'old':
                        vehicle_type = vehicle.vehicle_type.vehicle_type if vehicle.vehicle_type else ''
                    elif vehicle.vehicle_system in ['new', 'pradesh']:
                        if vehicle.heavy:
                            vehicle_type = dict(vehicle._fields['heavy'].selection).get(vehicle.heavy)
                        elif vehicle.four_wheeler:
                            vehicle_type = dict(vehicle._fields['four_wheeler'].selection).get(vehicle.four_wheeler)
                        elif vehicle.two_wheeler:
                            vehicle_type = dict(vehicle._fields['two_wheeler'].selection).get(vehicle.two_wheeler)

                    daily_data.append({ 
                        'date': current_date, 
                        'date_bs': convert_to_bs_date(current_date), 
                        'vehicle_number': vehicle.final_number, 
                        'vehicle_type': vehicle_type or 'N/A', 
                        'trips_count': trips_count, 
                        'load_capacity': load_capacity, 
                        'used_capacity': avg_used_capacity, 
                        'utilization': round(utilization, 2) 
                    }) 
                    print("Daily Data:", daily_data)

        # Filter by utilization if needed
        filtered_data = []
        for entry in daily_data:
            if self.filter_by == 'utilization':
                utilization = entry['utilization']
                if self.utilization_range == 'low' and 0 <= utilization <= 50:
                    filtered_data.append(entry)
                elif self.utilization_range == 'medium' and 50 < utilization <= 80:
                    filtered_data.append(entry)
                elif self.utilization_range == 'high' and utilization > 80:
                    filtered_data.append(entry)
            else:
                filtered_data.append(entry)
        print("Filtered Data:", filtered_data)

        if not filtered_data:
            raise UserError(_("No data found for the selected criteria."))
        return filtered_data

    def print_report(self):
        self.ensure_one()
        date_today = fields.Date.today()
        date_today_bs = convert_to_bs_date(date_today)
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'date_from_bs': self.date_from_bs,
                'date_to_bs': self.date_to_bs,
                'vehicle_id': self.vehicle_id.ids,
                'filter_by': self.filter_by,
                'date_today': date_today_bs,
                'vehicle_data': self._get_vehicle_data(),
            },
        }
        print("Report data:", data)
        
        return self.env.ref(
            'transport_management.action_vehicle_utilization_report').report_action(
                self, data=data)

    
    def export_to_excel(self):
        """Generate and download Excel report."""
        self.ensure_one()
        report_data = self._get_vehicle_data()

        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Vehicle Utilization Report")

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F0F0F0',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        number_format = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0.00'
        })

        # Set column widths
        worksheet.set_column('A:A', 15)  # Date
        worksheet.set_column('B:B', 25)  # Vehicle No
        worksheet.set_column('C:C', 15)  # Vehicle Type
        worksheet.set_column('D:D', 12)  # Trips
        worksheet.set_column('E:F', 15)  # Capacities
        worksheet.set_column('G:G', 15)  # Utilization

        # Write headers
        headers = [
            "मिति (Date)",
            "सवारी नं. (Vehicle No.)",
            "सवारी प्रकार (Vehicle Type)",
            "यात्रा संख्या (Trips)",
            "लोड क्षमता (Load Capacity) kg",
            "प्रयोग क्षमता (Used Capacity) kg",
            "उपयोग % (Utilization %)"
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data
        for row, data in enumerate(report_data, start=1):
            worksheet.write(row, 0, data['date_bs'], cell_format)
            worksheet.write(row, 1, data['vehicle_number'], cell_format)
            worksheet.write(row, 2, data['vehicle_type'], cell_format)
            worksheet.write(row, 3, data['trips_count'], cell_format)
            worksheet.write(row, 4, data['load_capacity'], number_format)
            worksheet.write(row, 5, data['used_capacity'], number_format)
            worksheet.write(row, 6, data['utilization'], number_format)

        # Write summary row
        if report_data:
            total_row = len(report_data) + 1
            total_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'bg_color': '#fafafa',
                'num_format': '#,##0'
            })
            
            total_trips = sum(d['trips_count'] for d in report_data)
            
            worksheet.write(total_row, 0, "जम्मा (Total)", total_format)
            worksheet.write_blank(total_row, 1, None, total_format)
            worksheet.write_blank(total_row, 2, None, total_format)
            worksheet.write(total_row, 3, total_trips, total_format)
            worksheet.write_blank(total_row, 4, None, total_format)
            worksheet.write_blank(total_row, 5, None, total_format)
            worksheet.write_blank(total_row, 6, None, total_format)

        workbook.close()
        
        # Get the Excel content
        excel_data = output.getvalue()
        output.close()

        # Generate filename
        filename = f"Vehicle_Utilization_Report_{self.date_from or 'all'}_to_{self.date_to or 'all'}.xlsx"

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })

        # Return the download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/binary/download_and_delete/{attachment.id}',
            'target': 'self',
        }