from odoo import models, fields, api
import calendar
from datetime import datetime, timedelta
import nepali_datetime
from odoo.exceptions import ValidationError
import base64
import imghdr
import os
from dateutil.relativedelta import relativedelta
from nepali_datetime import date as nepali_date
from ..models.maintenance_management import convert_to_bs_date

# Function to parse Nepali date
def parse_nepali_date(nepali_date_str):
    # Replace '/' with '-' if necessary
    nepali_date_str = nepali_date_str.replace('/', '-')
    year, month, day = map(int, nepali_date_str.split('-'))
    return nepali_datetime.date(year, month, day) 

# Function to convert Gregorian date to Nepali
def gregorian_to_nepali(gregorian_date):
    return (gregorian_date.year, gregorian_date.month, gregorian_date.day)   

# Fuel Type Province Cost
class FuelTypeProvinceCost(models.Model):
    _name = 'fuel.type.province.cost'
    _description = 'Fuel Cost by Province'
    _sql_constraints = [
        ('unique_province_per_fuel', 'UNIQUE(fuel_type_id, province_id)',
         'Each province can only have one price per fuel type!'),
    ]

    fuel_type_id = fields.Many2one('fuel.types', required=True)
    is_electric = fields.Boolean(
        string='Is Electric',
        related='fuel_type_id.is_electric',
        readonly=True,
        store=True
    )
    province_id = fields.Many2one('location.province', required=True, string="Province")
    cost_per_liter = fields.Float(string='Cost Per Liter (NPR)', required=True, digits=(12, 2))
    cost_per_hour = fields.Float(string='Cost per Hour (NPR)')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

# Fuel Types Model
class FuelTypes(models.Model):
    _name = 'fuel.types'
    _description = 'Fuel Types'
    _rec_name = 'name'
    
    name = fields.Char(string='Fuel Name', required=True)
    is_electric = fields.Boolean(
        string='Is Electric', 
        help="Check if the fuel type is electric"
    )
    # New field: For EVs, you can store the charger power (in kW)
    charger_power = fields.Float(
        string="Charger Power (kW)",
        help="For electric vehicles, the charging station power rating used to compute kWh delivered"
    )
    province_cost_ids = fields.One2many(
        'fuel.type.province.cost', 
        'fuel_type_id', 
        string="Province Prices"
    )
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

# Payment Mode Model
class PaymentMode(models.Model):
    _name = 'payment.mode'
    _description = 'Payment Mode'

    name = fields.Char(string='Payment Mode', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

# Fuel Entry Model
class FuelEntry(models.Model): 
    _name = 'fuel.entry' 
    _description = 'Fuel Entry & Tracking' 

    date = fields.Date(string='Date', required=True) 
    date_bs = fields.Char( 
        string='Date (BS)', 
        required=True, 
        compute='_compute_date_bs', 
        store=True 
    ) 
    time = fields.Char(string="Time", required=True) 
    vehicle_id = fields.Many2one('vehicle.number', string='Vehicle', required=True, ondelete='cascade') 
    driver_id = fields.Many2one('driver.details', string='Driver', required=True) 

    fuel_station_province = fields.Many2one( 
        'location.province', 
        string='Fuel Station Province', 
        required=True 
    ) 
    fuel_station_district = fields.Many2one( 
        'location.district', 
        string='Fuel Station District', 
        required=True, 
        domain="[('province_name', '=', fuel_station_province)]" 
    ) 
    fuel_station_municipality = fields.Many2one( 
        'location.palika', 
        string='Fuel Station Municipality/VDC', 
        required=True, 
        domain="[('district_name', '=', fuel_station_district)]" 
    ) 
    fuel_station_ward = fields.Char(string='Fuel Station Ward No.', required=True) 

    fuel_type_id = fields.Many2one('fuel.types', string='Fuel Type', required=True) 

    is_electric = fields.Boolean( 
        string='Is Electric', 
        related='fuel_type_id.is_electric', 
        readonly=True, 
        store=True 
    ) 
    cost_rate = fields.Float( 
        string='Cost Rate (NPR)', 
        compute="_compute_cost_rate", 
        store=True, 
        readonly=True 
    ) 
    # For non-electric vehicles, use quantity (liters) 
    quantity = fields.Float(string='Quantity (Liters)') 
    # For electric vehicles, the charging duration (hours) 
    hours_consumed = fields.Float(string='Hours Consumed') 
    rate_per_hour = fields.Float(string='Rate Per Hour (NPR)') 
    
    total_cost = fields.Float( 
        string='Total Cost (NPR)', 
        compute="_compute_total_cost", 
        store=True, 
    ) 
    payment_mode_id = fields.Many2one('payment.mode', string='Payment Mode', required=True) 
    receipt_upload = fields.Binary(string='Receipt Upload') 
    receipt_upload_filename = fields.Char("Receipt File Name") 
    receipt_upload_preview = fields.Html( 
        string="Receipt Preview", 
        compute="_compute_receipt_preview", 
        store=True, 
        sanitize=False, 
        help="Preview of the uploaded receipt." 
    ) 

    daily_fuel_consumed = fields.Float( 
        string='Daily Fuel Consumed', 
        compute="_compute_daily_fuel_consumed", 
        store=True, 
        help="Sum of fuel quantity for non-electric fuel entries for the same date." 
    ) 

    kwh_consumed = fields.Float( 
        string='Electricity Consumed (kWh)', 
        compute="_compute_kwh_consumed", 
        store=True, 
        help="Calculated as hours charged multiplied by the charger power (kW)." 
    ) 
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company) 

    current_odometer = fields.Float(string='Current Odometer Reading (Km)', required=True) 
    remarks = fields.Text(string='Remarks') 
    mileage = fields.Float( 
        string='Mileage (Km/Liter)', 
        compute="_compute_mileage", 
        store=True, 
        help="Calculated as distance traveled divided by fuel consumed." 
    ) 
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company) 

    is_today = fields.Boolean(string='Is Today', compute='_compute_date_filters', store=True) 
    is_this_week = fields.Boolean(string='Is This Week', compute='_compute_date_filters', store=True) 
    is_this_month = fields.Boolean(string='Is This Month', compute='_compute_date_filters', store=True) 

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    # Method to set receipt filename
    def _set_receipt_filename(self, vals):
        """
        Helper method to set receipt filename if not provided.
        """
        if vals.get('receipt_upload') and not vals.get('receipt_upload_filename'):
            try:
                receipt_data = base64.b64decode(vals.get('receipt_upload'))
                receipt_type = imghdr.what(None, h=receipt_data)
                if receipt_type:
                    vals['receipt_upload_filename'] = f"receipt.{receipt_type}"
                else:
                    vals['receipt_upload_filename'] = "receipt.png"
            except Exception:
                vals['receipt_upload_filename'] = "receipt.png"
        return vals

    # Method to update budget expenses
    def _update_budget_expenses(self, record):
        """
        Helper method to update actual fuel expenses on the corresponding budget.
        """
        budget = self.env['fuel.budget'].search([
            ('vehicle_id', '=', record.vehicle_id.id),
            ('date', '<=', record.date),
        ])
        if budget:
            budget._compute_actual_fuel_expenses()

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------
    # Method to compute date filters
    @api.depends('date')
    def _compute_date_filters(self):
        today = fields.Date.context_today(self)
        # print(f"Today's Date: {today}") 
        for record in self:
            # print(f"Processing Record ID: {record.id}, Date: {record.date}") 
            record.is_today = record.date == today
            # print(f"is_today: {record.is_today}") 
            if record.date:
                dt_date = fields.Date.from_string(record.date)
                dt_today = fields.Date.from_string(today)
                start_of_week = dt_today - timedelta(days=(dt_today.weekday() + 1) % 7)
                end_of_week = start_of_week + timedelta(days=6)
                # print(f"Start of Week: {start_of_week}, End of Week: {end_of_week}") 
                record.is_this_week = start_of_week <= dt_date <= end_of_week
                # print(f"is_this_week: {record.is_this_week}") 
                
                today_nepali_date = nepali_datetime.date.from_datetime_date(today)
                # print(f"Today's Nepali Date: {today_nepali_date}") 
                date_bs_nepali = parse_nepali_date(record.date_bs)
                # print(f"Date's Nepali Date: {date_bs_nepali}") 
                start_of_month = today_nepali_date.replace(day=1)
                # print(f"Start of Month: {start_of_month}") 
                start_of_month_nepali_tuple = gregorian_to_nepali(start_of_month)
                start_of_month_nepali = nepali_date(
                    start_of_month_nepali_tuple[0], 
                    start_of_month_nepali_tuple[1], 
                    start_of_month_nepali_tuple[2]
                )
                # print(f"Start of Month (Nepali): {start_of_month_nepali}") 
                record.is_this_month = date_bs_nepali >= start_of_month_nepali
                # record.is_this_month = (dt_date.year == dt_today.year and dt_date.month == dt_today.month) 
                # print(f"is_this_month: {record.is_this_month}") 
            else:
                record.is_today = False
                record.is_this_week = False
                record.is_this_month = False

    # Method to compute receipt preview
    @api.depends('receipt_upload', 'receipt_upload_filename')
    def _compute_receipt_preview(self):
        for record in self:
            if record.receipt_upload:
                if not record.id or not str(record.id).isdigit():
                    record.receipt_upload_preview = (
                        '<span style="display:inline-block; vertical-align:middle;">'
                        'Preview not available until saved'
                        '</span>'
                    )
                    continue
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                receipt_url = f"{base_url}/web/image?model={record._name}&id={record.id}&field=receipt_upload"
                record.receipt_upload_preview = (
                    f'<span style="display:inline-block; vertical-align:middle;">'
                    f'<a href="{receipt_url}" target="_blank">'
                    f'<img src="{receipt_url}" style="max-height:64px; max-width:64px; object-fit:contain;"/>'
                    '</a></span>'
                )
            else:
                record.receipt_upload_preview = (
                    '<span style="display:inline-block; vertical-align:middle;">'
                    'No receipt available'
                    '</span>'
                )

    # Method to compute mileage
    @api.depends('current_odometer', 'quantity', 'vehicle_id', 'is_electric')
    def _compute_mileage(self):
        """ 
        Calculate vehicle mileage by comparing current and previous odometer readings. 
        Mileage is only calculated for non-electric vehicles with fuel consumption. 
        """
        for record in self:
            # Skip calculation for electric vehicles or entries without quantity 
            if record.is_electric or record.quantity <= 0:
                record.mileage = 0.0
                continue
            # Find the previous fuel entry for the same vehicle with a lower odometer reading 
            previous_entry = self.search([
                ('vehicle_id', '=', record.vehicle_id.id),
                ('current_odometer', '<', record.current_odometer),
                ('is_electric', '=', False)
            ], order='current_odometer DESC', limit=1)
            # Calculate mileage if a previous entry exists 
            if previous_entry:
                distance_traveled = record.current_odometer - previous_entry.current_odometer
                record.mileage = distance_traveled / record.quantity if record.quantity > 0 else 0.0
            else:
                # If no previous entry, set mileage to 0 
                record.mileage = 0.0

    # Method to compute cost rate
    @api.depends('fuel_station_province', 'fuel_type_id', 'rate_per_hour')
    def _compute_cost_rate(self):
        for record in self:
            if record.fuel_type_id and record.is_electric:
                # For EVs, fetch the cost per hour for charging 
                ft_cost = self.env['fuel.type.province.cost'].search([
                    ('fuel_type_id', '=', record.fuel_type_id.id),
                    ('province_id', '=', record.fuel_station_province.id)
                ], limit=1)
                record.rate_per_hour = ft_cost.cost_per_hour if ft_cost else 0.0
                record.cost_rate = record.rate_per_hour
            elif record.fuel_station_province and record.fuel_type_id:
                # For conventional fuels, fetch the cost per liter 
                ft_cost = self.env['fuel.type.province.cost'].search([
                    ('fuel_type_id', '=', record.fuel_type_id.id),
                    ('province_id', '=', record.fuel_station_province.id)
                ], limit=1)
                record.cost_rate = ft_cost.cost_per_liter if ft_cost else 0.0
            else:
                record.cost_rate = 0.0

    # Method to compute total cost
    @api.depends('quantity', 'hours_consumed', 'cost_rate', 'fuel_type_id')
    def _compute_total_cost(self):
        for record in self:
            if record.fuel_type_id and record.fuel_type_id.is_electric:
                # For electric vehicles, compute cost based on charging hours. 
                record.total_cost = record.hours_consumed * record.rate_per_hour
            else:
                # For conventional fuels, compute cost based on quantity (liters). 
                record.total_cost = record.quantity * record.cost_rate

    # Method to compute daily fuel consumed
    @api.depends('date', 'quantity', 'is_electric', 'vehicle_id')
    def _compute_daily_fuel_consumed(self):
        for record in self:
            if record.date and record.vehicle_id and not record.is_electric:
                entries = self.search([
                    ('date', '=', record.date),
                    ('vehicle_id', '=', record.vehicle_id.id),
                    ('is_electric', '=', False)
                ])
                record.daily_fuel_consumed = sum(entries.mapped('quantity'))
            else:
                record.daily_fuel_consumed = 0.0

    # Method to compute kwh consumed
    @api.depends('hours_consumed', 'fuel_type_id.charger_power')
    def _compute_kwh_consumed(self):
        """ 
        For electric vehicles, compute the energy delivered in kWh. 
        If a charger power (kW) is defined in the fuel type, use it; otherwise, assume a default value (e.g., 7 kW). 
        """
        for record in self:
            if record.fuel_type_id and record.fuel_type_id.is_electric:
                charger_power = record.fuel_type_id.charger_power or 7.0
                record.kwh_consumed = record.hours_consumed * charger_power
            else:
                record.kwh_consumed = 0.0

    # Method to compute date_bs
    @api.depends('date')
    def _compute_date_bs(self):
        for record in self:
            record.date_bs = convert_to_bs_date(record.date)

    # -------------------------------------------------------------------------
    # Action Methods
    # -------------------------------------------------------------------------
    # Method to convert time to 12-hour format
    def convert_to_12hour_format(self, time_input):
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

    # Method to generate fuel history
    def _generate_fuel_history(self):
        for entry in self:
            fuel_station = ", ".join([
                entry.fuel_station_province.name,
                entry.fuel_station_district.district_name,
                entry.fuel_station_municipality.palika_name,
                f"Ward {entry.fuel_station_ward}"
            ])
            
            converted_time = self.convert_to_12hour_format(entry.time) if entry.time else 'N/A'
            vals = {
                'fuel_entry_id': entry.id,
                'vehicle_id': entry.vehicle_id.id,
                'date': entry.date,
                'date_bs': entry.date_bs,
                'time': converted_time,
                'driver_id': entry.driver_id.id,
                'fuel_station': fuel_station,
                'fuel_type_id': entry.fuel_type_id.id,
                'total_cost': entry.total_cost,
                'payment_mode_id': entry.payment_mode_id.id,
            }
              
            if entry.is_electric:
                vals.update({
                    'hours_consumed': entry.hours_consumed,
                    'rate_per_hour': entry.rate_per_hour,
                })
            else:
                vals.update({
                    'quantity': entry.quantity,
                    'cost_rate': entry.cost_rate,
                })

            # Check if a history record already exists for this entry 
            existing_history = self.env['fuel.history'].search([
                ('fuel_entry_id', '=', entry.id),
            ], limit=1)
            # print(f"Existing history record for entry {entry.id}: {existing_history}") 
            if existing_history:
                existing_history.write(vals)
            else:
                self.env['fuel.history'].create(vals)
                # print(f"Created history record for entry {entry.id}") 

    # Method to update the corresponding dashboard record
    def _update_dashboard(self):
        """Helper method to create or update the corresponding dashboard record."""
        for entry in self:
            # print(f"\nUpdating dashboard for Fuel Entry ID: {entry.id}") 
            fuel_station = ", ".join(filter(None, [
                entry.fuel_station_province.name if entry.fuel_station_province else "",
                entry.fuel_station_district.district_name if entry.fuel_station_district else "",
                entry.fuel_station_municipality.palika_name if entry.fuel_station_municipality else "",
                f"Ward {entry.fuel_station_ward}" if entry.fuel_station_ward else ""
            ]))
            
            dashboard_vals = {
                'fuel_entry_id': entry.id,
                'date': entry.date,
                'date_bs': entry.date_bs,
                'time': entry.time,
                'vehicle_id': entry.vehicle_id.final_number if entry.vehicle_id else "",
                'driver_id': entry.driver_id.name if entry.driver_id else "",
                'fuel_station': fuel_station,
                'fuel_type_id': entry.fuel_type_id.name if entry.fuel_type_id else "",
                'is_electric': entry.is_electric,
                'cost_rate': entry.cost_rate,
                'quantity': entry.quantity,
                'hours_consumed': entry.hours_consumed,
                'rate_per_hour': entry.rate_per_hour,
                'total_cost': entry.total_cost,
                'payment_mode_id': entry.payment_mode_id.name if entry.payment_mode_id else "",
                'current_odometer': entry.current_odometer,
                'mileage': entry.mileage,
            }
 
            # print(f"Dashboard Values: {dashboard_vals}") 
            dashboard = self.env['fuel.entry.dashboard'].search([('fuel_entry_id', '=', entry.id)], limit=1)
            if dashboard:
                # print(f"Existing dashboard record found (ID: {dashboard.id}), updating...") 
                dashboard.write(dashboard_vals)
            else:
                # print("No existing dashboard record found, creating a new one...") 
                self.env['fuel.entry.dashboard'].create(dashboard_vals)
            # print("Dashboard update completed.\n") 

    # -------------------------------------------------------------------------
    # ORM Overrides
    # -------------------------------------------------------------------------
    # Override the create method
    @api.model
    def create(self, vals):
        vals = self._set_receipt_filename(vals)
        record = super(FuelEntry, self).create(vals)
        # Generate history record 
        record._generate_fuel_history()
        record._update_dashboard()
        record.vehicle_id._compute_latest_mileage()
        record.vehicle_id._compute_monthly_fuel_consumed()
        self._update_budget_expenses(record)
        return record

    # Override the write method
    def write(self, vals):
        vals = self._set_receipt_filename(vals)
        res = super(FuelEntry, self).write(vals)
        self._generate_fuel_history()
        self._update_dashboard()
        for rec in self:
            self._update_budget_expenses(rec)
            self.vehicle_id._compute_latest_mileage()
            self.vehicle_id._compute_monthly_fuel_consumed()
        return res

    # Override the unlink method
    def unlink(self):
        # print("Unlinking fuel entries...") 
        for entry in self:
            # Search for matching fuel history records using the fuel_entry_id 
            history_records = self.env['fuel.history'].search([
                ('fuel_entry_id', '=', entry.id),
            ])
            # print(f"Found {len(history_records)} history records for entry {entry.id}") 
            history_records.unlink()
            # print(f"Deleted {len(history_records)} history records for entry {entry.id}") 
        return super(FuelEntry, self).unlink()

    # Method to validate receipt file
    @api.constrains('receipt_upload', 'receipt_upload_filename')
    def _check_receipt_upload_file(self):
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'svg'}
        for record in self:
            if record.receipt_upload:
                if not record.receipt_upload_filename:
                    raise ValidationError("Please provide a receipt file name.")
                file_extension = os.path.splitext(record.receipt_upload_filename)[1][1:].lower()
                if file_extension not in allowed_extensions:
                    raise ValidationError(
                        "Invalid receipt file type! Only PNG, JPG, JPEG, GIF, BMP, TIF, TIFF, WEBP and SVG files are allowed."
                    )

    # Method to validate consumption values
    @api.constrains('quantity', 'hours_consumed')
    def _check_consumption_values(self):
        for record in self:
            if not record.is_electric and record.quantity <= 0:
                raise ValidationError('Fuel quantity must be greater than zero')
            if record.is_electric and record.hours_consumed <= 0:
                raise ValidationError('Charging hours must be greater than zero')

    # Method to automatically load driver and fuel type from the selected vehicle
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        """Automatically load driver and fuel type from the selected vehicle."""
        if self.vehicle_id:
            self.driver_id = self.vehicle_id.driver_id
            self.fuel_type_id = self.vehicle_id.fuel_type
        else:
            self.driver_id = False
            self.fuel_type_id = False

    # Method to clear district and municipality when province changes
    @api.onchange('fuel_station_province')
    def _onchange_fuel_station_province(self):
        """Clear district and municipality when province changes."""
        self.fuel_station_district = False
        self.fuel_station_municipality = False

    # Method to clear municipality when district changes
    @api.onchange('fuel_station_district')
    def _onchange_fuel_station_district(self):
        """Clear municipality when district changes."""
        self.fuel_station_municipality = False

class MileageReport(models.Model):
    _name = 'mileage.report'
    _description = 'Mileage Calculation & Efficiency Reports'

    date = fields.Date(string='Date', required=True)
    date_bs = fields.Char(string='Date (BS)', required=True, compute='_compute_date_bs', store=True)
    vehicle_id = fields.Many2one('vehicle.number', string='Vehicle', required=True, ondelete='cascade')
    last_odometer = fields.Float(string='Last Odometer Reading (Km)', required=True)
    current_odometer = fields.Float(string='Current Odometer Reading (Km)', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    fuel_consumed_monthly = fields.Float(
        string='Monthly Energy Consumed',
        compute="_compute_fuel_consumed_monthly", 
        store=True,
        help="Total fuel/electricity consumed by the vehicle in the given month."
    )

    consumed_unit = fields.Char(
        string="Consumed Unit", 
        compute="_compute_units", 
        help="Displays 'kWh' for electric vehicles and 'L' for conventional vehicles."
    )

    fuel_consumed_display = fields.Char(
        string="Monthly Energy Consumed",
        compute="_compute_fuel_consumed_display",
        store=True,
        help="Concatenates fuel consumed and unit, e.g., '45 L' or '30 kWh'."
    )

    distance_travelled = fields.Float(
        string='Distance Traveled (Km)', 
        compute="_compute_distance", 
        store=True
    )

    average_efficiency_monthly = fields.Float(
        string='Average Monthly Efficiency (Km per unit)',
        compute="_compute_efficiency_monthly", 
        store=True,
        help="Calculates efficiency over a month instead of daily."
    )

    efficiency_unit = fields.Char(
        string="Efficiency Unit", 
        compute="_compute_units", 
        help="Displays 'km/L' for conventional vehicles and 'km/kWh' for electric vehicles."
    )

    efficiency_display = fields.Char(
        string="Efficiency",
        compute="_compute_efficiency_display",
        store=True,
        help="Shows efficiency value with its corresponding unit (e.g., '12 km/L')."
    )

    @api.depends('fuel_consumed_monthly', 'consumed_unit')
    def _compute_fuel_consumed_display(self):
        for record in self:
            fuel_amount = round(record.fuel_consumed_monthly, 2) if record.fuel_consumed_monthly else 0.0
            record.fuel_consumed_display = f"{fuel_amount} {record.consumed_unit}" if record.consumed_unit else f"{fuel_amount}"

    @api.depends('date')
    def _compute_date_bs(self):
        for record in self:
            record.date_bs = convert_to_bs_date(record.date)
    @api.depends('last_odometer', 'current_odometer')
    def _compute_distance(self):
        for record in self:
            record.distance_travelled = record.current_odometer - record.last_odometer

    @api.depends('date', 'vehicle_id')
    def _compute_fuel_consumed_monthly(self):
        """
        Compute the total fuel/electricity consumed for the vehicle in the given month.
        """
        for record in self:
            if record.date and record.vehicle_id:
                first_day_of_month = record.date.replace(day=1)
                last_day_of_month = (first_day_of_month + timedelta(days=31)).replace(day=1) - timedelta(days=1)
                
                fuel_entries = self.env['fuel.entry'].search([
                    ('date', '>=', first_day_of_month),
                    ('date', '<=', last_day_of_month),
                    ('vehicle_id', '=', record.vehicle_id.id)
                ])
                
                electric_entries = fuel_entries.filtered(lambda x: x.is_electric)
                non_electric_entries = fuel_entries.filtered(lambda x: not x.is_electric)
                
                record.fuel_consumed_monthly = sum(electric_entries.mapped('kwh_consumed')) if electric_entries else sum(non_electric_entries.mapped('quantity'))
            else:
                record.fuel_consumed_monthly = 0.0

    @api.depends('distance_travelled', 'fuel_consumed_monthly') 
    def _compute_efficiency_monthly(self):
        for record in self:
            record.average_efficiency_monthly = (record.distance_travelled / record.fuel_consumed_monthly) if record.fuel_consumed_monthly else 0.0

    @api.depends('vehicle_id')
    def _compute_units(self):
        for record in self:
            if record.vehicle_id and hasattr(record.vehicle_id, 'fuel_type'):
                if record.vehicle_id.fuel_type.is_electric:
                    record.consumed_unit = "kWh"
                    record.efficiency_unit = "km/kWh"
                else:
                    record.consumed_unit = "L"
                    record.efficiency_unit = "km/L"
            else:
                record.consumed_unit = "L"
                record.efficiency_unit = "km/L"

    @api.depends('average_efficiency_monthly', 'efficiency_unit')
    def _compute_efficiency_display(self):
        for record in self:
            record.efficiency_display = f"{record.average_efficiency_monthly:.2f} {record.efficiency_unit}"

# Fuel Budget Model
class FuelBudget(models.Model):
    _name = 'fuel.budget'
    _description = 'Fuel Budgeting & Cost Control'

    date = fields.Date(string='Date', required=True)
    date_bs = fields.Char(string='Date (BS)', required=True, compute='_compute_date_bs', store=True)
    vehicle_id = fields.Many2one('vehicle.number', string='Vehicle', required=True, ondelete='cascade')
    monthly_fuel_budget = fields.Float(string='Monthly Fuel Budget (NPR)', required=True)
    actual_fuel_expenses = fields.Float(
        string='Actual Fuel Expenses (NPR)', 
        compute='_compute_actual_fuel_expenses', 
        store=True,
        help="Total fuel cost recorded in Fuel Entry for the selected vehicle and month."
    )
    budget_deviation = fields.Float(
        string="Budget Deviation (Rs)", 
        compute='_compute_budget_deviation', 
        store=True
    )
    budget_deviation_report = fields.Text(
        string='Budget Deviation Report', 
        compute='_compute_budget_deviation_report', 
        store=True
    )
    anomalies_fraud_detection = fields.Text(string='Anomalies & Fraud Detection', compute='compute_anomalies_fraud_detection', store=True)
    anomaly_flag = fields.Boolean(string='Anomaly Flag', compute='compute_anomaly_flag', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    # Method to compute anomaly flag
    @api.depends('actual_fuel_expenses', 'monthly_fuel_budget')
    def compute_anomaly_flag(self):
        for record in self:
            if record.actual_fuel_expenses > record.monthly_fuel_budget:
                record.anomaly_flag = True
            else:
                record.anomaly_flag = False
    
    # Method to compute anomalies and fraud detection
    @api.depends('actual_fuel_expenses', 'monthly_fuel_budget')
    def compute_anomalies_fraud_detection(self):
        for record in self:
            if record.actual_fuel_expenses > record.monthly_fuel_budget:
                record.anomalies_fraud_detection = "Exceeds Budget"
            else:
                record.anomalies_fraud_detection = "Within Budget"
    
    # Method to compute date_bs
    @api.depends('date')
    def _compute_date_bs(self):
        for record in self:
            record.date_bs = convert_to_bs_date(record.date)

    # Method to compute budget deviation
    @api.depends('monthly_fuel_budget', 'actual_fuel_expenses')
    def _compute_budget_deviation(self):
        for record in self:
            record.budget_deviation = record.monthly_fuel_budget - record.actual_fuel_expenses

    # Method to compute actual fuel expenses
    @api.depends('date', 'vehicle_id')
    def _compute_actual_fuel_expenses(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.date_bs and record.vehicle_id:
                # date_obj = fields.Date.from_string(record.date) 
                # start_date = date_obj.replace(day=1)
                # last_day = calendar.monthrange(date_obj.year, date_obj.month)[1] 
                # end_date = date_obj.replace(day=last_day)
                
                today_nepali_date = nepali_datetime.date.from_datetime_date(today)
                # print(f"Today's Nepali Date: {today_nepali_date}")
                date_bs_nepali = parse_nepali_date(record.date_bs)
                # print(f"Date's Nepali Date: {date_bs_nepali}")
                start_of_month = today_nepali_date.replace(day=1)
                # print(f"Start of Month: {start_of_month}")
                start_of_month_nepali_tuple = gregorian_to_nepali(start_of_month)
                start_of_month_nepali = nepali_date(
                    start_of_month_nepali_tuple[0],
                    start_of_month_nepali_tuple[1],
                    start_of_month_nepali_tuple[2]
                )
                # print(f"Start of Month (Nepali): {start_of_month_nepali}")
                if today_nepali_date.month == 12:
                    # For the last month of the year, set next month to the first month of next year
                    next_month = today_nepali_date.replace(year=today_nepali_date.year + 1, month=1, day=1)
                    # print(f"Next Month: {next_month}")
                else:
                    # Otherwise, just increment the month and set day=1
                    next_month = today_nepali_date.replace(month=today_nepali_date.month + 1, day=1)
                    # print(f"Next Month: {next_month}")

                # Subtract one day to get the last day of the current month.
                end_of_month_nepali = next_month - timedelta(days=1)
                # print("End of Month (Nepali):", end_of_month_nepali)
                start_date = start_of_month_nepali.strftime('%Y-%m-%d')
                end_date = end_of_month_nepali.strftime('%Y-%m-%d')

                fuel_entries = self.env['fuel.entry'].search([ 
                    ('date_bs', '>=', start_date),
                    ('date_bs', '<=', end_date),
                    ('vehicle_id', '=', record.vehicle_id.id)
                ])
                record.actual_fuel_expenses = sum(fuel_entries.mapped('total_cost')) 
            else:
                record.actual_fuel_expenses = 0.0

    # Method to compute budget deviation
    @api.depends('monthly_fuel_budget', 'actual_fuel_expenses')
    def _compute_budget_deviation_report(self):
        for record in self:
            if record.actual_fuel_expenses > record.monthly_fuel_budget:
                deviation = record.actual_fuel_expenses - record.monthly_fuel_budget
                record.budget_deviation_report = (
                    "The actual fuel expenses exceed the monthly budget by %s NPR." % deviation
                )
            elif record.actual_fuel_expenses == record.monthly_fuel_budget:
                record.budget_deviation_report = "The actual fuel expenses equal the monthly budget."
            else:
                deviation = record.monthly_fuel_budget - record.actual_fuel_expenses
                record.budget_deviation_report = (
                    "The actual fuel expenses are less than the monthly budget by %s NPR." % deviation
                )

# Fuel History Model
class FuelHistory(models.Model):
    _name = 'fuel.history'
    _description = 'Fuel/Electricity Consumption History'
    _order = 'create_date desc'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    vehicle_id = fields.Many2one('vehicle.number', string='Vehicle', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    date_bs = fields.Char(string='Date (BS)', required=True, compute='_compute_date_bs', store=True)
    time = fields.Char(string='Time', required=True)
    driver_id = fields.Many2one('driver.details', string='Driver', required=True)
    fuel_station = fields.Char(string='Fuel/Charging Station', required=True)
    fuel_type_id = fields.Many2one('fuel.types', string='Fuel Type', required=True)
    quantity = fields.Float(string='Fuel Quantity (Liters)')
    cost_rate = fields.Float(string='Fuel Cost Rate (NPR)')
    hours_consumed = fields.Float(string='Charging Hours')
    rate_per_hour = fields.Float(string='EV Rate Per Hour (NPR)')
    total_cost = fields.Float(string='Total Cost (NPR)', required=True)
    payment_mode_id = fields.Many2one('payment.mode', string='Payment Mode', required=True)
    is_electric = fields.Boolean(
        string='Is Electric',
        related='fuel_type_id.is_electric',
        readonly=True,
        store=True
    )
    fuel_entry_id = fields.Many2one(
        'fuel.entry', 
        string='Fuel Entry', 
        ondelete='cascade'
    )
    is_today = fields.Boolean(string='Is Today', compute='_compute_date_filters', store=True)
    is_this_week = fields.Boolean(string='Is This Week', compute='_compute_date_filters', store=True)
    is_this_month = fields.Boolean(string='Is This Month', compute='_compute_date_filters', store=True)
    
    # Method to compute date_bs
    @api.depends('date')
    def _compute_date_bs(self):
        for record in self:
            record.date_bs = convert_to_bs_date(record.date)
    
    # Method to compute date filters
    @api.depends('date')
    def _compute_date_filters(self):
        # print("Compute Date Filters")
        today = fields.Date.context_today(self)
        for record in self:
            record.is_today = record.date == today

            if record.date:
                dt_date = fields.Date.from_string(record.date)
                dt_today = fields.Date.from_string(today)

                start_of_week = dt_today - timedelta(days=(dt_today.weekday() + 1) % 7)
                end_of_week = start_of_week + timedelta(days=6)
                record.is_this_week = start_of_week <= dt_date <= end_of_week
                
                today_nepali_date = nepali_datetime.date.from_datetime_date(today)
                # print(f"Today's Nepali Date: {today_nepali_date}")
                date_bs_nepali = parse_nepali_date(record.date_bs)
                # print(f"Date's Nepali Date: {date_bs_nepali}")
                start_of_month = today_nepali_date.replace(day=1)
                # print(f"Start of Month: {start_of_month}")
                start_of_month_nepali_tuple = gregorian_to_nepali(start_of_month)
                start_of_month_nepali = nepali_date(
                    start_of_month_nepali_tuple[0],
                    start_of_month_nepali_tuple[1],
                    start_of_month_nepali_tuple[2]
                )
                # print(f"Start of Month (Nepali): {start_of_month_nepali}")
                record.is_this_month = date_bs_nepali >= start_of_month_nepali
                # record.is_this_month = (dt_date.year == dt_today.year and dt_date.month == dt_today.month)
                # Assuming today_nepali_date is a nepali_datetime.date object for the current Nepali date
                # if today_nepali_date.month == 12:
                #     # For the last month of the year, set next month to the first month of next year
                #     next_month = today_nepali_date.replace(year=today_nepali_date.year + 1, month=1, day=1)
                #     # print(f"Next Month: {next_month}")
                # else:
                #     # Otherwise, just increment the month and set day=1
                #     next_month = today_nepali_date.replace(month=today_nepali_date.month + 1, day=1)
                #     # print(f"Next Month: {next_month}")

                # # Subtract one day to get the last day of the current month.
                # end_of_month_nepali = next_month - timedelta(days=1)
                # print(f"End of Month (Nepali): {end_of_month_nepali}")

            else:
                record.is_today = False
                record.is_this_week = False
                record.is_this_month = False  
    
    # Method to force recomputation of date filters
    def recompute_date_filters(self):
        """Method to force recomputation of date filters on all records."""
        records = self.search([])
        for rec in records:
            rec.write({'date': rec.date})

# Fuel Entry Dashboard Model
class FuelEntryDashboard(models.Model):
    _name = 'fuel.entry.dashboard'
    _description = 'Fuel Entry Dashboard'
    
    fuel_entry_id = fields.Integer(string='Fuel Entry ID', required=True)
    date = fields.Date(string='Date', required=True)
    date_bs = fields.Char(string='Date (BS)', required=True)
    time = fields.Char(string="Time", required=True)
    vehicle_id = fields.Char(string='Vehicle', required=True, 
                          help="Name or Identifier from vehicle record")
    driver_id = fields.Char(string='Driver', required=True, 
                         help="Name or Identifier from driver record")
    fuel_station = fields.Char(
        string='Fuel Station',
        required=True,
        help="Concatenated location: Province, District, Mu nicipality/VDC, and Ward"
    )
    fuel_type_id = fields.Char(string='Fuel Type', required=True)
    is_electric = fields.Boolean(string='Is Electric', required=True)
    cost_rate = fields.Integer(string='Cost Rate (NPR)', required=True)
    quantity = fields.Integer(string='Quantity (Liters)')
    hours_consumed = fields.Integer(string='Hours Consumed')
    rate_per_hour = fields.Integer(string='Rate Per Hour (NPR)')
    total_cost = fields.Integer(string='Total Cost (NPR)', required=True)
    payment_mode_id = fields.Char(string='Payment Mode', required=True)
    current_odometer = fields.Integer(string='Current Odometer Reading (Km)', required=True)
    mileage = fields.Integer(string='Mileage (Km/Liter)', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
