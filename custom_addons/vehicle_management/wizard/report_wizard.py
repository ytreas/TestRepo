from odoo import models, fields, api
import nepali_datetime

def convert_to_12hour_format(time_input):
        try:
            # print(f"Input received: {time_input}")
            if isinstance(time_input, (int, float)):
                time_value = float(time_input)
                # print(f"Numeric input converted to float: {time_value}")
            else:
                if ":" in time_input:
                    parts = time_input.split(':')
                    hour = int(parts[0])
                    minute = int(parts[1])
                    # print(f"String with colon detected. Hour: {hour}, Minute: {minute}")
                    time_value = hour + minute / 60.0
                    # print(f"Time value computed from string: {time_value}")
                elif time_input.strip() == "":
                    # print("Empty string provided, returning empty result.")
                    return ''
                else:
                    time_value = float(time_input)
                    # print(f"String numeric input converted to float: {time_value}")

            hour = int(time_value)
            minute = round((time_value - hour) * 60)
            # print(f"Extracted hour: {hour}, minute: {minute}")

            period = "AM" if hour < 12 or hour == 24 else "PM"
            if hour == 0 or hour == 24:
                display_hour = 12
            elif hour > 12:
                display_hour = hour - 12
            else:
                display_hour = hour
            # print(f"Converted to 12-hour format: {display_hour}:{minute:02d} {period}")

            return f"{display_hour}:{minute:02d} {period}"
        except Exception as e:
            # print(f"Error converting time: {e}")
            return time_input

class MovementDetailsWizard(models.TransientModel):
    _name = 'movement.details.wizard'
    _description = 'Movement Details Wizard'

    # Example fields for the wizard
    normal_date = fields.Date('Date')
    # normal_date_bs = fields.Char('Date BS:',compute='_compute_nepali_date', store=True)

    date_from = fields.Date('Date From', required = True)
    date_from_bs = fields.Char('Date From')
    date_to = fields.Date('Date To', required=True)
    date_to_bs = fields.Char("Date To")
    vehicle_number = fields.Many2one('vehicle.number', string='Vehicle Number')
    vehicle_company_id = fields.Many2one('custom.vehicle.company', string="Vehicle Company")
    available_vehicle_ids = fields.Many2many(
        'vehicle.number', 
        string="Available Vehicles", 
        compute="_compute_available_vehicle_ids", 
        store=True
    )

    @api.depends('vehicle_company_id')
    def _compute_available_vehicle_ids(self):
        for rec in self:
            if rec.vehicle_company_id:
                rec.available_vehicle_ids = rec.vehicle_company_id.vehicle_ids
            else:
                # Optionally, if no company is selected, you may want to show all vehicles.
                rec.available_vehicle_ids = self.env['vehicle.number'].search([])
    
    @api.onchange('vehicle_company_id')
    def _onchange_vehicle_company(self):
        self.vehicle_number = False

    # date_to = fields.Date('Date To')

    
    # @api.depends('normal_date')
    # def _compute_nepali_date(self):
    #     for record in self:
            # if record.date_en:
            #     route_nepali_date = nepali_datetime.date.from_datetime_date(record.date_en)
            #     record.date_bs = route_nepali_date.strftime('%Y-%m-%d')
            # else:
            #     record.date_bs = False

            # if record.normal_date:
            #     route_nepali_date = nepali_datetime.date.from_datetime_date(record.normal_date)
            #     record.normal_date_bs = route_nepali_date.strftime('%Y-%m-%d')
            # else:
            #     record.normal_date_bs = False

    def action_confirm(self):
        # Add logic to confirm and process the wizard data
        prepared_data = []
        domain = []
        vehicle_number = vehicle_type = vehicle_brand = engine_number = None
        chassis_number = driver_name = driver_license_number = 'N/A'
        
        if self.vehicle_number:
            domain.append(('vehicle_number', '=', self.vehicle_number.id))

            vehicle_info = self.env['vehicle.number'].search([('id', '=', self.vehicle_number.id)])
            vehicle_number = vehicle_info.final_number
            vehicle_brand = vehicle_info.vehicle_brand.brand_name_np
            engine_number = vehicle_info.vehicle_model.engine_number        
            chassis_number = vehicle_info.vehicle_model.chassis_number
            driver_name = vehicle_info.driver_id.name_np
            driver_license_number = vehicle_info.driver_id.license_number
            fuel_type = vehicle_info.fuel_type.name
       
            if vehicle_info.vehicle_system == 'old':
                vehicle_type = vehicle_info.vehicle_type.name_en
            elif vehicle_info.vehicle_system == 'new':
                vehicle_type = vehicle_info.vehicle_type.name_en
            else:
                if vehicle_info.heavy:
                    vehicle_type = vehicle_info.heavy
                elif vehicle_info.two_wheeler:
                    vehicle_type = vehicle_info.two_wheeler
                else:
                    vehicle_type = vehicle_info.four_wheeler

        if self.date_from or self.date_to:
            nepali_date_from = nepali_datetime.date.from_datetime_date(self.date_from)
            date_from= nepali_date_from.strftime('%Y-%m-%d')

            nepali_date_to = nepali_datetime.date.from_datetime_date(self.date_to)
            date_to = nepali_date_to.strftime('%Y-%m-%d')
            print("date_from",date_from,date_to)
            
            domain.append(('route_date_bs', '>=',date_from))
            domain.append(('route_date_bs', '<=',date_to))
        
        if self.vehicle_company_id:
            domain.append(('vehicle_number', 'in', self.vehicle_company_id.vehicle_ids.ids))

        date_bs = nepali_datetime.date.from_datetime_date(self.normal_date).strftime('%Y-%m-%d') if self.normal_date else ''

        vehicles = self.env['fleet.route'].search(domain)
        for vehicle in vehicles:
            # converted_time =  convert_to_12hour_format(vehicle.route_time_to) if vehicle.route_time_to else 'N/A'
            total_time = vehicle.total_hours
            prepared_data.append({
                'date': vehicle.route_date_bs,
                'route_time': total_time,
                'vehicle_number': vehicle.vehicle_number.final_number,
                'start_point': vehicle.source or 'N/A',
                'end_point': vehicle.destination or 'N/A',
                'purpose': vehicle.purpose or 'N/A',
                'distance': vehicle.route_length or 'N/A',
                'remarks': vehicle.remarks or 'N/A',
            })
        # print("############################",prepared_data)
        return {
            'type': 'ir.actions.report',
            'report_name': 'vehicle_management.action_report_vehicle_movement',
            'report_type': 'qweb-pdf',
            'data': {
                'company_name': self.env.company.name,
                'report_name': 'Vehicle Movement Report',
                'prepared_by': self.env.user.name,
                'date': date_bs,
                'prepared_data': prepared_data or [],
                'vehicle_number': vehicle_number or 'N/A',
                'vehicle_type': vehicle_type or 'N/A',
                'vehicle_brand': vehicle_brand or 'N/A',
                'engine_number': engine_number or 'N/A',
                'chassis_number': chassis_number or 'N/A',
                'driver_name': driver_name or 'N/A',
                'driver_license_number': driver_license_number or 'N/A',
                'fuel_type': fuel_type or 'N/A',
            },
        }





class FuelDetailsWizard(models.TransientModel):
    _name = 'fuel.details.wizard'
    _description = 'Fuel Details Wizard'

    filter_by = fields.Selection([
        ('date', 'Date'),
        ('vehicle', 'Vehicle'),
        ('location', 'Location'),
        ('fuel_type', 'Fuel Type'),
    ], string="Filter By", required=True, default='date')
    date_from = fields.Date(string="Date From", default=fields.Date.today)
    date_to = fields.Date(string="Date To", default=fields.Date.today)

    date_from_bs = fields.Char(string="Date From (BS)", compute="_compute_nepali_dates")
    date_to_bs = fields.Char(string="Date To (BS)", compute="_compute_nepali_dates")
    
    vehicle_id = fields.Many2one('vehicle.number', string="Vehicle")
    fuel_station_province = fields.Many2one('location.province', string='Fuel Station Province')
    fuel_station_district = fields.Many2one(
        'location.district',
        string='Fuel Station District',
        domain="[('province_name', '=', fuel_station_province)]"
    ) 
    fuel_station_municipality = fields.Many2one(
        'location.palika',
        string='Fuel Station Municipality/VDC',
        domain="[('district_name', '=', fuel_station_district)]"
    )
    department = fields.Char(string="Department/Unit", default="Transport Division")
    authorized_by = fields.Char(string="Authorized By", default="Transport Manager")
    date_today = fields.Date(string="Date", default=fields.Date.today, required=True)
    vehicle_company_id = fields.Many2one('custom.vehicle.company', string="Vehicle Company")
    available_vehicle_ids = fields.Many2many(
        'vehicle.number', 
        string="Available Vehicles", 
        compute="_compute_available_vehicle_ids", 
        store=True
    )
    fuel_type_id = fields.Many2one('fuel.types', string="Fuel Type")

    @api.depends('vehicle_company_id')
    def _compute_available_vehicle_ids(self):
        for rec in self:
            if rec.vehicle_company_id:
                rec.available_vehicle_ids = rec.vehicle_company_id.vehicle_ids
            else:
                # Optionally, if no company is selected, you may want to show all vehicles.
                rec.available_vehicle_ids = self.env['vehicle.number'].search([])

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
    
    @api.onchange('vehicle_company_id')
    def _onchange_vehicle_company(self):
        self.vehicle_id = False

    def action_confirm(self):
        domain = []
        if self.filter_by == 'date':
            if self.date_from and self.date_to:
                domain.append(('date', '>=', self.date_from))
                domain.append(('date', '<=', self.date_to))
        elif self.filter_by == 'vehicle' and self.vehicle_id:
            domain.append(('vehicle_id', '=', self.vehicle_id.id))
        elif self.filter_by == 'location':
            if self.fuel_station_province:
                domain.append(('fuel_station_province', '=', self.fuel_station_province.id))
            if self.fuel_station_district:
                domain.append(('fuel_station_district', '=', self.fuel_station_district.id))
            if self.fuel_station_municipality:
                domain.append(('fuel_station_municipality', '=', self.fuel_station_municipality.id))
        elif self.filter_by == 'fuel_type':
            if self.fuel_type_id:
                domain.append(('fuel_type_id', '=', self.fuel_type_id.id))

        if self.vehicle_company_id:
            domain.append(('vehicle_id', 'in', self.vehicle_company_id.vehicle_ids.ids))
        
        fuel_entries = self.env['fuel.entry'].search(domain)

        report_data = []
        for entry in fuel_entries:
            formatted_time = convert_to_12hour_format(entry.time)
            record = {
                'date': entry.date_bs,
                'vehicle_number': entry.vehicle_id.final_number if entry.vehicle_id else '',
                'driver_name': entry.driver_id.name if entry.driver_id else '',
                'engine_number': entry.vehicle_id.vehicle_model.engine_number if entry.vehicle_id else '',
                'fuel_type': entry.fuel_type_id.name if entry.fuel_type_id else '',
                'vehicle_brand': entry.vehicle_id.vehicle_brand.brand_name if entry.vehicle_id else '',
                'driver_license_number': entry.driver_id.license_number if entry.driver_id else '',
                'vehicle_type': entry.vehicle_id.vehicle_type.name_en if entry.vehicle_id else '',
                'time': formatted_time,
                'location': entry.fuel_station_municipality.palika_name_np or '',
                'fuel_filled': entry.quantity if not entry.is_electric else entry.hours_consumed,
                'odometer': entry.current_odometer,
                'amount': entry.total_cost,
                'remarks': entry.remarks or '',
            }
            report_data.append(record)

        # Convert current date to Nepali format for display
        date_bs = nepali_datetime.date.from_datetime_date(self.date_today).strftime('%Y-%m-%d')

        # Convert date range if needed
        date_from_bs = '' 
        date_to_bs = ''
        if self.filter_by == 'date' and self.date_from and self.date_to:
            date_from_bs = nepali_datetime.date.from_datetime_date(self.date_from).strftime('%Y-%m-%d')
            date_to_bs = nepali_datetime.date.from_datetime_date(self.date_to).strftime('%Y-%m-%d')

        filter_by = self.filter_by
        if self.filter_by == 'location':
            filter_by = 'Fuel Station'
        elif self.filter_by == 'vehicle':
            filter_by = 'Vehicle'
        else:
            filter_by = 'Date Range'
        data = {
            'company_name': self.env.company.name,
            'report_name': 'Vehicle Fuel Consumption Report',
            'prepared_by': self.env.user.name or 'N/A',
            'prepared_by_designation': self.env.user.job_title or 'N/A',
            'authorized_by': self.authorized_by or 'N/A',
            'department': self.department or 'N/A',
            'date_from': date_from_bs,
            'date_to': date_to_bs,
            'date': date_bs,
            'fuel_entries': report_data,
            'filter_by': filter_by,
        }

        if self.vehicle_id:
            vehicle = self.vehicle_id
            data.update({
                'vehicle_number': vehicle.final_number,
                'vehicle_type': vehicle.vehicle_type.name_en if hasattr(vehicle, 'vehicle_type') else 'N/A',
                'engine_number': vehicle.vehicle_model.engine_number if hasattr(vehicle, 'engine_number') else 'N/A',
                'chassis_number': vehicle.vehicle_model.chassis_number if hasattr(vehicle, 'chassis_number') else 'N/A',
                'vehicle_brand': vehicle.vehicle_brand.brand_name if hasattr(vehicle, 'brand_id') else 'N/A',
                'driver_name': vehicle.driver_id.name if hasattr(vehicle, 'driver_id') else 'N/A',
                'driver_license_number': vehicle.driver_id.license_number if hasattr(vehicle, 'driver_id') and hasattr(vehicle.driver_id, 'license_number') else 'N/A',
                'fuel_type': vehicle.fuel_type.name if hasattr(vehicle, 'fuel_type') else 'N/A',
            })

        return self.env.ref('vehicle_management.fuel_consumption_report_action').report_action(
            fuel_entries.ids,
            data=data
        )