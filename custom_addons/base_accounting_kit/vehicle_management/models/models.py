# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import time, datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import _
from odoo.exceptions import ValidationError
import nepali_datetime
import calendar
import os
import base64
import imghdr
import re
from nepali_datetime import date as nepali_date
from ..utils.dashboard_notification import Utilities 
from ..models.maintenance_management import convert_to_bs_date
from ..models.fuel_consumption import parse_nepali_date, gregorian_to_nepali

# Vehicle Number Model
class VehicleNumber(models.Model):
    _name = 'vehicle.number'
    _description = 'Vehicle Number'
    _rec_name = 'final_number'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    check_in_date = fields.Date(string='Check In Date')
    check_in_date_bs = fields.Char(string="Check In Date (Nepali)", compute='_compute_nepali_dates', store=True)
    check_in_time = fields.Char(string='Check In Time', compute='_compute_check_in_time', store=True)
    check_in_time_unformatted = fields.Char(string='Unformat Check In Time')

    arrival_date = fields.Date(string='Arrival Date')
    arrival_date_bs = fields.Char(string="Arrival Date (Nepali)")

    check_out_date = fields.Date(string='Check Out Date')
    check_out_date_bs = fields.Char(string='Check Out Date (Nepali)', compute='_compute_nepali_dates', store=True)
    check_out_time = fields.Char(string='Check Out Time',compute='_compute_check_out_time', store=True)
    check_out_time_unformatted = fields.Char(string='Unformat Check Out Time')

    check_in_bool = fields.Boolean(string='Check In', default=False)
    check_out_bool = fields.Boolean(string='Check Out', default=False)
    paid_bool = fields.Boolean(string='Paid', default=False)
    duration = fields.Float(string="Duration (Hours)", compute="_compute_duration", store=True)
    
    default_vehicle_number = fields.Many2one('vehicle.number',string='Vehicles Number')
    number = fields.Char(string="Number")
    hours = fields.Float(string='Hours', compute="_compute_duration", store=True)
    minutes = fields.Float(string='Minutes', compute="_compute_duration", store=True)
    seconds = fields.Float(string='Seconds', compute="_compute_duration", store=True)
    parking_cost = fields.Float(string='Parking Cost(NPR)')
    fine_cost = fields.Float(string='Fine Cost(NPR)',compute="_compute_fine_cost", store=True)
    total_cost = fields.Float(string='Total Cost(NPR)',compute="_compute_total_cost", store=True)

    state = fields.Selection([('draft','Draft'),('check_in','Check In'),('check_out','Check Out'),('payment','Payment')],string='State',default='draft',tracking= True)
    
    vehicle_type = fields.Many2one('custom.vehicle.type', string='Vehicle Type')
    volume = fields.Float(string='Volume', required=True, related='vehicle_type.max_weight')
    zonal_code = fields.Char(string = 'Zonal Code')
    vehicle_number = fields.Char(string='Vehicle Classification Code')
    driver_id = fields.Many2one('driver.details',string='Driver Name:')

    lot_number = fields.Char(string = 'Lot Number',size=2)
    custom_number = fields.Char(string ='Custom Number',size = 5)
    
    province = fields.Many2one('location.province', string='Province')
    province_code = fields.Char(string = 'Province Code')
    vehicle_code = fields.Char(string='Code')
    province_number = fields.Char(string='Province Number')
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
    
    final_number = fields.Char(string="Vehicle Number" ,  compute="_compute_final_number", store=True)
    fuel_type = fields.Many2one('fuel.types', string='Fuel Type')

    old_id = fields.Many2one(
        "vehicle.old.classification",
        string="Old Vehicle Classification"   
    )
    zonal_id = fields.Many2one(
        "vehicle.zonal.classification",
        string="Zone"
    )
    vehicle_classification = fields.Selection([
        ('private', 'Private'),
        ('public', 'Public'),
        ('government', 'Government'),
        ('other', 'Other')
    ], string='Vehicle Classification')

    vehicle_system = fields.Selection([
        ('old', 'Old Vehicle System'),
        ('pradesh', 'Pradesh Vehicle System'),
        ('new', 'Embossed System'),
    ],default='old', string='Vehicle System', required=True)

    # old_id = fields.Many2one("vehicle.old.classification", string="Old Vehicle Classification")
    new_id = fields.Many2one("vehicle.new.classification",string="New Vehicle Classification")
  

    vehicle_owner = fields.Many2one('custom.vehicle.owner', string='Vehicle Owner', domain="[('vehicle_company_id', '=', vehicle_company)]")
    vehicle_company = fields.Many2one('custom.vehicle.company', string='Vehicle Company')
    electric_vehicle_num = fields.Char(string='Electric Vehicle Number')



    office_code = fields.Char(string="Office Code")
    # paredesh_province_code = fields.Char(string = 'Province Code')
    # paredesh_vehicle_code = fields.Char(string='Code')


    bluebook_id = fields.One2many("custom.vehicle.bluebook", "vehicle_number", string="Bluebook")
    vehicle_permit_id = fields.One2many("custom.vehicle.permit", "vehicle_number", string="Permit")
    vehicle_pollution_id = fields.One2many("custom.vehicle.pollution", "vehicle_number", string="Pollution")
    vehicle_insurance_id = fields.One2many("custom.vehicle.insurance", "vehicle_number", string="Insurance")
    seat_no = fields.Integer(string="Total Seat")

    fine_penalty_id = fields.One2many("custom.fine.penalty","vehicle_number",string="Fine and Penalty")
    route_id = fields.One2many('fleet.route','vehicle_number',string='Route')


    # route_from = fields.Char(string="Route From:")
    # route_to = fields.Char(string="Route To:")
    # check_out_date = fields.Date(string='Check Out Date')
    # plan_date = fields.Date(string="Planned Date")
    # plan_date_bs = fields.Char(string="Planned Date (BS)",compute='_compute_nepali_dates', store=True)
    
    latest_bluebook_record = fields.Many2one('vehicle.due.details', string='Latest Bluebook Record',compute='_compute_latest_record')
    latest_pollution_record = fields.Many2one('vehicle.due.details', string='Latest Pollution Record',compute='_compute_latest_record')
    latest_insurance_record = fields.Many2one('vehicle.due.details', string='Latest Insurance Record',compute='_compute_latest_record')
    latest_permit_record = fields.Many2one('vehicle.due.details', string='Latest Permit Record', compute='_compute_latest_record')

    bluebook_expiry_date = fields.Char(string="Bluebook Expiry Date",related='latest_bluebook_record.expiry_date_bs')
    bluebook_renewal_date = fields.Char(string="Bluebook Renewal Date",related='latest_bluebook_record.renewal_date_bs')
    bluebook_renewal_cost = fields.Float(string="Bluebook Renewal Cost",related='latest_bluebook_record.renewal_cost')

    pollution_expiry_date = fields.Char(string="Pollution Expiry Date",related='latest_pollution_record.expiry_date_bs')
    pollution_renewal_date = fields.Char(string="Pollution Renewal Date",related='latest_pollution_record.renewal_date_bs')
    pollution_renewal_cost = fields.Float(string="Pollution Renewal Cosrt",related='latest_pollution_record.renewal_cost')

    insurance_expiry_date = fields.Char(string="Insurance Expiry Date",related='latest_insurance_record.expiry_date_bs')
    insurance_renewal_date = fields.Char(string="Insurance Renewal Date",related='latest_insurance_record.renewal_date_bs')
    insurance_renewal_cost = fields.Float(string="Insurance Renewal Cost",related='latest_insurance_record.renewal_cost')


    permit_expiry_date = fields.Char(string="Permit Expiry Date",related='latest_permit_record.expiry_date_bs')
    permit_renewal_date = fields.Char(string="Permit Renewal Date",related='latest_permit_record.renewal_date_bs')
    permit_renewal_cost = fields.Float(string="Permit Renewal Cost",related='latest_permit_record.renewal_cost')

    vehicle_image = fields.Binary(string="Image", attachment=True)
    image_preview = fields.Html(
        string="Image Preview", 
        compute="_compute_image_preview", 
        sanitize=False, 
        store=True
    )
    vehicle_image_filename = fields.Char("Image File Name")
    # The code `is_upcoming_expiry` appears to be a variable or function name in Python. Without
    # seeing the actual implementation of this variable or function, it is not possible to determine
    # exactly what it is doing. The name suggests that it might be related to checking if an expiry
    # date is upcoming, but the functionality would depend on how it is implemented in the code.
    is_upcoming_expiry = fields.Boolean(string="Upcoming Bluebook Expiry", store=True)

    upcoming_permit_expiry = fields.Boolean(string="Upcoming Bluebook Expiry", store=True)
    upcoming_insurance_expiry = fields.Boolean(string="Upcoming Insurance Expiry", store=True)
    upcoming_pollution_expiry = fields.Boolean(string="Upcoming Pollution Expiry", store=True)



    # @api.depends('bluebook_expiry_date')
    # def _compute_is_upcoming_expiry(self):
    #     print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    #     today = fields.Date.today()
    #     today_bs = nepali_datetime.date.from_datetime_date(today)
    #     today_bs_str = today_bs.strftime('%Y-%m-%d')
    #     for record in self:
    #         if record.bluebook_expiry_date:
    #             expiry_date = record.bluebook_expiry_date

    #             year, month, day = map(int, expiry_date.split('-'))
    #             expiry_date_obj = nepali_datetime.date(year, month, day)
    #             # Calculate the Nepali date 30 days from today
    #             future_date_obj = today_bs + timedelta(days=30)
    #             record.is_upcoming_expiry = today_bs <= expiry_date_obj <= future_date_obj
    #         else:
    #             record.is_upcoming_expiry = False



    service_scheduling_ids = fields.One2many(
        'service.scheduling', 'vehicle_id', string='Service Schedulings'
    )
    service_execution_ids = fields.One2many(
        'service.execution', 'vehicle_id', string='Service Executions'
    )

    latest_service_scheduling_id = fields.Many2one(
        'service.scheduling', 
        string='Latest Service Scheduling', 
        compute='_compute_latest_service_scheduling', 
        store=False
    )
    last_service_date = fields.Date(
        string='Last Service Date', 
        compute='_compute_latest_service_scheduling', 
        store=True
    )
    next_service_due_date = fields.Date(
        string='Next Service Due Date', 
        compute='_compute_latest_service_scheduling', 
        store=True
    )
    maintenance_request_ids = fields.One2many(
        'maintenance.request', 
        'vehicle_id', 
        string='Maintenance Requests'
    )
    latest_maintenance_date = fields.Date(
        string="Latest Scheduled Maintenance Date", 
        compute="_compute_latest_maintenance_date", 
        store=True
    )
    latest_maintenance_date_bs = fields.Char(
        string="Latest Scheduled Maintenance Date (BS)", 
        compute="_compute_latest_maintenance_date", 
        store=True
    )

    fuel_entry_ids = fields.One2many('fuel.entry', 'vehicle_id', string='Fuel Entries')

    monthly_fuel_consumed = fields.Float(
        string="Monthly Fuel/Electricity Consumed", 
        compute="_compute_monthly_fuel_consumed", 
        store=True,
        help="Sum of fuel quantity (L) for conventional vehicles or electricity consumed (kWh) for EVs in the current month."
    )

    fuel_unit = fields.Char(
        string="Fuel Unit",
        compute="_compute_fuel_unit",
        store=True,
        help="Displays 'kWh' for electric vehicles and 'Liters' for conventional vehicles."
    )

    fuel_consumed_display = fields.Char(
        string="Fuel Consumed (Current Month)",
        compute="_compute_display_fuel_consumed",
        store=True,
        help="Displays the total fuel/electricity consumed in the current month with its unit."
    )

    mileage_report_ids = fields.One2many('mileage.report', 'vehicle_id', string="Mileage Reports")

    latest_mileage_report_id = fields.Many2one(
        'mileage.report', string="Latest Mileage Report", compute="_compute_latest_mileage_report", store=False
    )

    latest_odometer = fields.Float(
        string="Latest Odometer Reading (Km)", compute="_compute_latest_mileage_report", store=True
    )
    # latest_distance_travelled = fields.Float(
    #     string="Latest Distance Travelled (Km)", compute="_compute_latest_distance_travelled", store=True
    # )
    latest_average_efficiency_monthly = fields.Float(
        string="Latest Monthly Efficiency (Km per unit)", compute="_compute_latest_mileage_report", store=True
    )

    consumed_unit = fields.Char(
        string="Consumed Unit",
        compute="_compute_consumed_unit",
        store=True,
        help="Displays 'kWh' for electric vehicles and 'L' for conventional vehicles."
    )

    efficiency_display = fields.Char(
        string="Efficiency",
        compute="_compute_efficiency_display",
        store=True,
        help="Concatenates the latest monthly efficiency and its unit (e.g., '15 km/L' or '7 km/kWh')."
    )

    vehicle_brand = fields.Many2one("vehicle.brand", string="Vehicle Brand")
    vehicle_model = fields.Many2one("vehicle.model", string="Vehicle Model")
    vehicle_cc = fields.Integer(string="Vehicle CC", related="vehicle_model.cc")
    service_duration = fields.Char(string="Service Duration(Months)")
    last_service_odometer = fields.Float(
        string="Last Servicing Odometer (Km)",
        compute="_compute_last_service_odometer",
        store=True
    )
    email_to = fields.Char(string="Email", related="vehicle_owner.email")
    mileage = fields.Float(
        string='Latest Mileage (Km/L)',
        compute='_compute_latest_mileage',
        store=True,
        help="Latest mileage based on the most recent fuel entry."
    )
    
    total_distance_travelled = fields.Float(
        string="Total Distance Travelled",
        compute="_compute_latest_distance_travelled",
        store=True
    )
    
    # Method to compute the last service odometer
    @api.depends('service_execution_ids.odometer_reading')
    def _compute_last_service_odometer(self):
        for vehicle in self:
            latest_service = self.env['service.execution'].search(
                [('vehicle_id', '=', vehicle.id)], 
                order='start_time desc', 
                limit=1
            )
            print("latest service odometer", latest_service.odometer_reading)
            vehicle.last_service_odometer = latest_service.odometer_reading if latest_service else 0.0

    # Method to compute the total distance travelled
    @api.depends('fuel_entry_ids.current_odometer')
    def _compute_latest_distance_travelled(self):
        for vehicle in self:
            latest_service = self.env['service.execution'].search(
                [('vehicle_id', '=', vehicle.id)],
                order='end_time desc',
                limit=1
            )

            if latest_service:
                last_service_odometer = latest_service.odometer_reading or 0.0
                fuel_entries = self.env['fuel.entry'].search(
                    [('vehicle_id', '=', vehicle.id), ('date', '>=', latest_service.end_time)],
                    order='date asc'
                )

                if fuel_entries:
                    total_distance = 0.0
                    previous_odometer = last_service_odometer
                    for entry in fuel_entries:
                        if entry.current_odometer > previous_odometer:
                            total_distance += entry.current_odometer - previous_odometer
                            previous_odometer = entry.current_odometer
                    
                    vehicle.total_distance_travelled = total_distance
                else:
                    vehicle.total_distance_travelled = 0.0
            else:
                vehicle.total_distance_travelled = 0.0

    # Method to compute the latest mileage
    def _compute_latest_mileage(self):
        """Fetch the latest fuel entry for the vehicle and update mileage."""
        for record in self:
            latest_fuel_entry = self.env['fuel.entry'].search(
                [('vehicle_id', '=', record.id)],
                order="date desc, id desc",
                limit=1
            )
            record.mileage = latest_fuel_entry.mileage if latest_fuel_entry else 0.0
            
    # Method to handle changes in vehicle brand
    @api.onchange('vehicle_brand')
    def _onchange_vehicle_brand(self):
        self.vehicle_model = False
        domain = []
        if self.vehicle_brand:
            domain = [('brand_id', '=', self.vehicle_brand.id)]
        return {
            'domain': {
                'vehicle_model': domain
            }
        }

    # Method to compute the image preview
    @api.depends('vehicle_image', 'vehicle_image_filename')
    def _compute_image_preview(self):
        for record in self:
            if record.vehicle_image:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                image_url = f"{base_url}/web/image?model={record._name}&id={record.id}&field=vehicle_image"
                record.image_preview = f"""
                    <div style="text-align: center;">
                        <a href="{image_url}" target="_blank">
                            <img src="{image_url}" style="max-height: 70px; max-width: 70px; object-fit: contain;"/>
                        </a>
                    </div>
                """
            else:
                record.image_preview = "<div>No image available</div>"

    # Method to validate vehicle image
    @api.constrains('vehicle_image', 'vehicle_image_filename')
    def _check_vehicle_image_file(self):
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'svg'}
        for record in self:
            if record.vehicle_image:
                if not record.vehicle_image_filename:
                    raise ValidationError("Please provide an image file name.")
                file_extension = os.path.splitext(record.vehicle_image_filename)[1][1:].lower()
                if file_extension not in allowed_extensions:
                    raise ValidationError("Invalid image file type! Only PNG, JPG, JPEG, GIF, BMP, TIF, TIFF, WEBP and SVG files are allowed.")

    # Method to generate service requests
    def _generate_service_requests(self):
        for vehicle in self.search([]):
            latest_service = self.env['service.execution'].search(
                [('vehicle_id', '=', vehicle.id)],
                order='start_time desc',
                limit=1
            )
    
            latest_bluebook = self.env['custom.vehicle.bluebook'].search([('vehicle_number.id', '=' ,vehicle.id)],limit=1)  
            if latest_bluebook.expiry_date:
                date_diff = latest_bluebook.expiry_date -  fields.Date.today()
                default_expiry = latest_bluebook.expiry_date + relativedelta(months=3)
                if timedelta(days=0) <= date_diff <= timedelta(days=7):
                    bluebook = self.env['custom.vehicle.bluebook'].create({
                        'vehicle_company_id':vehicle.vehicle_company.id,
                        'owner_id':vehicle.vehicle_owner.id,
                        'vehicle_number': vehicle.id,  
                        'last_renewal_date': latest_bluebook.last_renewal_date, 
                        'expiry_date': default_expiry,
                        # 'due_details':due_details.id,
                        'renewal_cost': 0.0,
                        'renewed': False,
                    })
                    if bluebook:
                        due_details = self.env['vehicle.due.details'].search([(
                            'bluebook_id', '=' ,bluebook.id,
                        )])
                        if due_details:
                            due_details.write({
                                'due_status':'upcoming',
                            })
                elif date_diff < timedelta(days=0):
                    fine_cost = 100  
                    
                    latest_bluebook.write({
                        'fine_cost': fine_cost,
                        # 'due_details.due_status':'overdue',
                        # 'remarks': 'Renewal overdue, fine applied', 
                        # 'renewed': False,  
                    })
                    due_details = self.env['vehicle.due.details'].search([(
                        'bluebook_id', '=' ,latest_bluebook.id,
                    )])
                    if due_details:
                        due_details.write({
                            'due_status':'overdue',
                        })
            else:
                print("The expiry date is not within the next 7 days.")
                
            if not latest_service:
                continue
            last_service_date = latest_service.start_time
            last_service_odometer = latest_service.odometer_reading if latest_service.odometer_reading else 0.0
            print("Last service date:", last_service_date)
            print("Last service odometer:", last_service_odometer)
            if last_service_date:
                # 🔹 Get fuel entries since the last service
                fuel_entries = self.env['fuel.entry'].search(
                    [('vehicle_id', '=', vehicle.id), ('date', '>=', last_service_date)],
                    order="date asc" 
                )
                print("Fuel entries:", fuel_entries)

                # 🔹 Compute total distance traveled since last service
                total_distance_travelled = 0.0
                if fuel_entries:
                    previous_odometer = last_service_odometer
                    print("Previous odometer:", previous_odometer)
                    for entry in fuel_entries:
                        print("inside for loop")
                        if entry.current_odometer > previous_odometer:
                            print("inside if loop")
                            total_distance_travelled += entry.current_odometer - previous_odometer
                            print("Total distance travelled:", total_distance_travelled)
                            previous_odometer = entry.current_odometer
                            print("Previous odometer:", previous_odometer)
                try:
                    service_months = int(vehicle.service_duration) if vehicle.service_duration else 3
                except ValueError:
                    service_months = 3
                    
                next_service_date = last_service_date + relativedelta(months=service_months)
                time_condition = fields.Date.today() >= next_service_date
        
                service_type = vehicle.service_scheduling_ids.mapped('service_type_id')[:1]
                distance_condition = total_distance_travelled  >= 5000
       
                # Check if a service request already exists but is not yet executed
                existing_scheduled_service = self.env['service.scheduling'].search([
                    ('vehicle_id', '=', vehicle.id),
                    ('next_service_due_date', '=', latest_service.start_time),
                    ('state', '=', 'draft')
                ], limit=1)
                print("Existing scheduled service:", existing_scheduled_service)
                if not existing_scheduled_service and (time_condition or distance_condition):
                    service = self.env['service.scheduling'].create({
                        'vehicle_id': vehicle.id,
                        'last_service_date': latest_service.start_time,
                        'next_service_due_date': fields.Date.today(),
                        'service_type_id': [(6, 0, [service_type.id])],
                        'notification_mode_id': 1,
                    })
                    if service:
                        utilities = Utilities(self.env)
                        expiry_date = latest_service.service_date_bs
                        vehicle_number = latest_service.vehicle_id.final_number
                        utilities.showNotificationDashboard(date = expiry_date, vehicle_number = vehicle_number,renewal_type = 'service', driver_name = None)

                # Send email notification using the email template
                # mail_template = self.env.ref('vehicle_management.email_template_service_scheduled')
                # print("mail_template", mail_template)

                # if mail_template:
                #     print("Email template found")

                #     # Send mail
                #     mail_template.send_mail(vehicle.id, force_send=True)

                #     # Generate email content
                #     email_values = mail_template.with_context(lang=self.env.user.lang).generate_email(vehicle.id)
                #     rendered_body = email_values.get('body_html', '')  # Safely retrieve body_html
                #     print("Rendered body:", rendered_body)

                #     print("Email sent")
                # else:
                # Option 2: Alternatively, create and send a mail.mail record directly
                    mail_values = {
                        'subject': 'Service Scheduled Notification',
                        'body_html': (
                            f'<p>Dear {vehicle.vehicle_owner.name},</p>'
                            f'<p>Your service for the vehicle {vehicle.final_number} has been scheduled.</p>'
                            f'<p>Please check the service details in your portal.</p>'
                            f'<p>Thank you,</p>'
                            f'<p>{vehicle.company_id.name}</p>'
                        ),
                        'email_to': vehicle.vehicle_owner.email,
                        'model': 'vehicle.number',
                        'res_id': vehicle.id, 
                    }
                    print("mail_values", mail_values)

                    mail = self.env['mail.mail'].create(mail_values)
                    print("mail", mail)

                    mail.send()
                    print("Email sent")

    # Compute latest mileage report
    @api.depends('mileage_report_ids')
    def _compute_latest_mileage_report(self):
        for vehicle in self:
            if vehicle.mileage_report_ids:
                latest_report = vehicle.mileage_report_ids.sorted(
                    key=lambda r: r.date or fields.Date.from_string('1900-01-01'),
                    reverse=True
                )[0]
                vehicle.latest_mileage_report_id = latest_report.id
                vehicle.latest_odometer = latest_report.current_odometer
                vehicle.latest_average_efficiency_monthly = latest_report.average_efficiency_monthly
                # vehicle.latest_distance_travelled = latest_report.distance_travelled
            else:
                vehicle.latest_mileage_report_id = False
                vehicle.latest_odometer = 0.0
                vehicle.latest_average_efficiency_monthly = 0.0
                # vehicle.latest_distance_travelled = 0.0

    # Compute consumed unit
    @api.depends('latest_mileage_report_id')
    def _compute_consumed_unit(self):
        for record in self:
            if record.latest_mileage_report_id:
                record.consumed_unit = record.latest_mileage_report_id.consumed_unit
            else:
                record.consumed_unit = "L"

    # Method to compute the efficiency display
    @api.depends('mileage', 'consumed_unit')
    def _compute_efficiency_display(self):
        for record in self:
            eff = round(record.mileage, 2) if record.mileage else 0.0
            record.efficiency_display = f"{eff} km/{record.consumed_unit}"

    # Method to compute the monthly fuel consumed
    @api.depends('fuel_entry_ids.date', 'fuel_entry_ids.quantity', 'fuel_entry_ids.kwh_consumed', 'fuel_entry_ids.is_electric')
    def _compute_monthly_fuel_consumed(self):
        today = fields.Date.today()
        if isinstance(today, str):
            today = datetime.strptime(today, "%Y-%m-%d").date()
        today_nepali_date = nepali_datetime.date.from_datetime_date(today)
        # print(f"Today's Nepali Date: {today_nepali_date}")
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
        end_of_month = next_month - timedelta(days=1)
        # print(f"End of Month: {end_of_month}")
        first_day = start_of_month_nepali.strftime("%Y-%m-%d")
        # print(f"First Day: {first_day}")
        last_day = end_of_month.strftime("%Y-%m-%d")
        # print(f"Last Day: {last_day}")
        first_day_date = fields.Date.from_string(first_day)
        # print(f"First Day Date: {first_day_date}")
        last_day_date = fields.Date.from_string(last_day)
        # print(f"Last Day Date: {last_day_date}")
        # first_day = today.replace(day=1)
        # last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        for vehicle in self:
            monthly_total = 0.0
            entries = vehicle.fuel_entry_ids.filtered(
                lambda e: e.date_bs and first_day_date <= fields.Date.from_string(e.date_bs) <= last_day_date
            )
            for entry in entries:
                if entry.is_electric:
                    monthly_total += entry.kwh_consumed
                else:
                    monthly_total += entry.quantity
            vehicle.monthly_fuel_consumed = monthly_total
            # print(f"Monthly Fuel Consumed for {vehicle.final_number}: {monthly_total}")

    # Method to compute the fuel unit
    @api.depends('fuel_entry_ids', 'fuel_type')
    def _compute_fuel_unit(self):
        for record in self:
            if hasattr(record, 'fuel_type') and record.fuel_type:
                record.fuel_unit = "kWh" if record.fuel_type.is_electric else "Liters"
            else:
                electric_entries = record.fuel_entry_ids.filtered(lambda x: x.is_electric)
                record.fuel_unit = "kWh" if electric_entries else "Liters"

    # Method to compute the fuel consumed display
    @api.depends('monthly_fuel_consumed', 'fuel_unit')
    def _compute_display_fuel_consumed(self):
        for record in self:
            consumption = round(record.monthly_fuel_consumed, 2)
            record.fuel_consumed_display = f"{consumption} {record.fuel_unit}"

    # Method to compute the latest maintenance date
    @api.depends('maintenance_request_ids.scheduled_start')
    def _compute_latest_maintenance_date(self):
        print("inside the function")
        for vehicle in self:
            latest_request = self.env['maintenance.request'].search([
                ('vehicle_id', '=', vehicle.id),
                ('scheduled_start', '!=', False)
            ], order='scheduled_start desc', limit=1)
            print("latest request", latest_request.vehicle_id)

            if latest_request:
                vehicle.latest_maintenance_date = latest_request.scheduled_start
                if latest_request.scheduled_start:
                    nepali_date = nepali_datetime.date.from_datetime_date(latest_request.scheduled_start)
                    vehicle.latest_maintenance_date_bs = nepali_date.strftime('%Y-%m-%d')
                else:
                    vehicle.latest_maintenance_date_bs = False
            else:
                vehicle.latest_maintenance_date = False
                vehicle.latest_maintenance_date_bs = False

    # Method to compute the latest service scheduling
    @api.depends('service_scheduling_ids.last_service_date', 'service_scheduling_ids.next_service_due_date')
    def _compute_latest_service_scheduling(self):
        for record in self:
            if record.service_scheduling_ids:
                latest_sched = record.service_scheduling_ids.sorted(
                    key=lambda s: s.last_service_date or fields.Date.from_string('1900-01-01'),
                    reverse=True
                )[0]
                record.latest_service_scheduling_id = latest_sched.id
                record.last_service_date = latest_sched.last_service_date
                record.next_service_due_date = latest_sched.next_service_due_date
            else:
                record.latest_service_scheduling_id = False
                record.last_service_date = False
                record.next_service_due_date = False

    # Override the name_search method
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            recs = self.search([('final_number', operator, name)] + args, limit=limit)
        else:
            recs = self.search(args, limit=limit)

        unique = {}
        for rec in recs:
            key = (rec.final_number or '').strip()
            if key and key not in unique:
                unique[key] = rec.id

        result = [(rec_id, vehicle_num) for vehicle_num, rec_id in unique.items()]

        if not result:
            result = super(VehicleNumber, self).name_search(name, args, operator, limit)
        return result

    # Override the name_get method
    def name_get(self):
        result = []
        for rec in self:
            name = rec.final_number or ''
            result.append((rec.id, name))
        return result

    # Method to compute the latest record
    def _compute_latest_record(self):
        for record in self:
            due_details_model = self.env['vehicle.due.details']
            record.latest_bluebook_record = due_details_model.get_latest_record(record.id, 'bluebook')
            record.latest_pollution_record = due_details_model.get_latest_record(record.id, 'pollution')
            record.latest_insurance_record = due_details_model.get_latest_record(record.id, 'insurance')
            record.latest_permit_record = due_details_model.get_latest_record(record.id, 'permit')
    

    # Method to convert string to time
    def _str_to_time(self, time_str):
        try:
            return datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError:
            return None

   
    # Override the create method to perform additional actions 
    @api.model
    def create(self, vals):
        # Auto-compute the image filename if an image is provided and filename is missing
        if vals.get('vehicle_image') and not vals.get('vehicle_image_filename'):
            try:
                image_data = base64.b64decode(vals.get('vehicle_image'))
                image_type = imghdr.what(None, h=image_data)
                if image_type:
                    vals['vehicle_image_filename'] = f"image.{image_type}"
                else:
                    vals['vehicle_image_filename'] = "image.png"
            except Exception:
                vals['vehicle_image_filename'] = "image.png"

        # Create the record
        records = super(VehicleNumber, self).create(vals)
       
        # Call existing methods (if needed)
        records.change_vehicle_number()
        records.check_default_vehicle_number_()
        records._compute_image_preview()

        # New logic: Update vehicle owner and company
        for record in records:
            if record.vehicle_owner:
                record.vehicle_owner.write({
                    'vehicle_number': [(4, record.id)],
                })
            if record.vehicle_company:
                record.vehicle_company.write({
                    'vehicle_ids': [(4, record.id)],
                })
        
        if self.driver_id:
            self.env['driver.performance'].create({
                'driver_id': records.driver_id.id,
                'route': records.route_id.id,
                'checkpoints': records.route_id.checkpoints.id,
            })
            self.env['duty.allocation'].create({
                'driver_id': records.driver_id.id,
                'vehicle_id': records.id,
            })
        return records
    
    # Override the write method to perform additional actions
    def write(self, vals):
        if 'vehicle_image' in vals:
            try:
                image_data = base64.b64decode(vals.get('vehicle_image'))
                image_type = imghdr.what(None, h=image_data)
                if image_type:
                    vals['vehicle_image_filename'] = f"image.{image_type}"
                else:
                    vals['vehicle_image_filename'] = "image.png"
            except Exception:
                vals['vehicle_image_filename'] = "image.png"
        
        result = super(VehicleNumber, self).write(vals)

        if 'vehicle_image' in vals:
            self._compute_image_preview()

        return result


    # def write(self,vals):
    #     self.compute_is_upcoming_expiry()  


    # Method to handle the 'fuel_type' field
    @api.onchange('fuel_type')
    def _onchange_fuel_type(self):
        if self.fuel_type:
            # Assuming "electricity" is a value in the 'fuel.types' model.
            electricity_fuel_type = self.env['fuel.types'].search([('name', '=', 'Electricity')], limit=1)
            if electricity_fuel_type:
                self.electric_vehicle_num = f"(electric) {self.final_number}"
        else:
            self.electric_vehicle_num = False  # Clear fuel_type if electric_vehicle_num is empty

    # Method to handle the 'default_vehicle_number' field
    @api.model
    def check_default_vehicle_number(self):
        if self.default_vehicle_number:
            vehicle_number = self.default_vehicle_number
            if vehicle_number:
                existing_vehicle_number = self.env['vehicle.number'].sudo().search([
                    ('final_number', '=', self.default_vehicle_number.final_number),
                ], limit=1)
              
                if existing_vehicle_number:
                    if existing_vehicle_number.vehicle_system == "old":
                        self.vehicle_classification = existing_vehicle_number.vehicle_classification
                        # self.mobile_number = existing_vehicle_number.mobile_number
                        self.vehicle_type = existing_vehicle_number.vehicle_type
                        self.zonal_id = existing_vehicle_number.zonal_id
                        self.lot_number = existing_vehicle_number.lot_number
                        self.zonal_code = existing_vehicle_number.zonal_code
                        self.vehicle_number = existing_vehicle_number.vehicle_number
                        self.vehicle_system = existing_vehicle_number.vehicle_system
                        self.custom_number = existing_vehicle_number.custom_number
                        
                    elif existing_vehicle_number.vehicle_system == "pradesh":
                        self.vehicle_classification = existing_vehicle_number.vehicle_classification
                        self.province = existing_vehicle_number.province
                        self.vehicle_type = existing_vehicle_number.vehicle_type
                        self.vehicle_number = existing_vehicle_number.vehicle_number
                        self.province_code = existing_vehicle_number.province_code
                        # self.mobile_number = existing_vehicle_number.mobile_number
                        self.vehicle_system = existing_vehicle_number.vehicle_system
                        self.custom_number = existing_vehicle_number.custom_number
                        self.lot_number = existing_vehicle_number.lot_number
                        self.office_code = existing_vehicle_number.office_code
                    else:
                        self.province = existing_vehicle_number.province
                        self.vehicle_type = existing_vehicle_number.vehicle_type
                        self.heavy = existing_vehicle_number.heavy
                        self.two_wheeler = existing_vehicle_number.two_wheeler
                        self.four_wheeler = existing_vehicle_number.four_wheeler
                        self.province_code = existing_vehicle_number.province_code
                        self.province_number = existing_vehicle_number.province_number
                        # self.mobile_number = existing_vehicle_number.mobile_number
                        self.vehicle_system = existing_vehicle_number.vehicle_system
                        self.custom_number = existing_vehicle_number.custom_number
                else:
                    print("No matching vehicle found.")

    # Method to handle the 'default_vehicle_number' field
    @api.onchange('default_vehicle_number')
    def onchange_default_vehicle_number(self):
        print("On chnange vehicle Number",self.default_vehicle_number)
        if self.default_vehicle_number:
            vehicle_number = self.default_vehicle_number
            if vehicle_number:
                existing_vehicle_number = self.env['vehicle.number'].sudo().search([
                    ('final_number', '=', vehicle_number.final_number),
                ], limit=1)
              
                if existing_vehicle_number:
                    if existing_vehicle_number.vehicle_system == "old":
                        self.vehicle_classification = existing_vehicle_number.vehicle_classification
                        # self.mobile_number = existing_vehicle_number.mobile_number
                        self.vehicle_type = existing_vehicle_number.vehicle_type
                        self.zonal_id = existing_vehicle_number.zonal_id
                        self.lot_number = existing_vehicle_number.lot_number
                        self.zonal_code = existing_vehicle_number.zonal_code
                        self.vehicle_number = existing_vehicle_number.vehicle_number
                        self.vehicle_system = existing_vehicle_number.vehicle_system
                        self.custom_number = existing_vehicle_number.custom_number
                        
                    elif existing_vehicle_number.vehicle_system == "pradesh":
                        self.vehicle_classification = existing_vehicle_number.vehicle_classification
                        self.province = existing_vehicle_number.province
                        self.vehicle_type = existing_vehicle_number.vehicle_type
                        self.vehicle_number = existing_vehicle_number.vehicle_number
                        self.province_code = existing_vehicle_number.province_code
                        # self.mobile_number = existing_vehicle_number.mobile_number
                        self.vehicle_system = existing_vehicle_number.vehicle_system
                        self.custom_number = existing_vehicle_number.custom_number
                        self.lot_number = existing_vehicle_number.lot_number
                        self.office_code = existing_vehicle_number.office_code
                    else:
                        self.province = existing_vehicle_number.province
                        self.vehicle_type = existing_vehicle_number.vehicle_type
                        self.heavy = existing_vehicle_number.heavy
                        self.two_wheeler = existing_vehicle_number.two_wheeler
                        self.four_wheeler = existing_vehicle_number.four_wheeler
                        self.province_code = existing_vehicle_number.province_code
                        self.province_number = existing_vehicle_number.province_number
                        # self.mobile_number = existing_vehicle_number.mobile_number
                        self.vehicle_system = existing_vehicle_number.vehicle_system
                        self.custom_number = existing_vehicle_number.custom_number
                else:
                    print("No matching vehicle found.")

    # Method to handle the 'default_vehicle_number' field
    @api.model
    def check_default_vehicle_number_(self):
        if self.default_vehicle_number:
            vehicle_number = self.default_vehicle_number
            if vehicle_number:
                existing_vehicle_number = self.env['vehicle.number'].sudo().search([
                    ('final_number', '=', self.default_vehicle_number.final_number),
                ], limit=1)
              
                if existing_vehicle_number:
                    if existing_vehicle_number.vehicle_system == "old":
                        self.vehicle_classification = existing_vehicle_number.vehicle_classification
                        # self.mobile_number = existing_vehicle_number.mobile_number
                        self.vehicle_type = existing_vehicle_number.vehicle_type
                        self.zonal_id = existing_vehicle_number.zonal_id
                        self.lot_number = existing_vehicle_number.lot_number
                        self.zonal_code = existing_vehicle_number.zonal_code
                        self.vehicle_number = existing_vehicle_number.vehicle_number
                        self.province_code = existing_vehicle_number.province_code
                        self.vehicle_code = existing_vehicle_number.vehicle_code
                        self.province_number = existing_vehicle_number.province_number
                        self.vehicle_system = existing_vehicle_number.vehicle_system
                    else:
                        self.province = existing_vehicle_number.province
                        self.vehicle_type = existing_vehicle_number.vehicle_type
                        self.heavy = existing_vehicle_number.heavy
                        self.two_wheeler = existing_vehicle_number.two_wheeler
                        self.four_wheeler = existing_vehicle_number.four_wheeler
                        self.province_code = existing_vehicle_number.province_code
                        self.province_number = existing_vehicle_number.province_number
                        # self.mobile_number = existing_vehicle_number.mobile_number
                        self.vehicle_system = existing_vehicle_number.vehicle_system
                    self.custom_number = existing_vehicle_number.custom_number
                else:
                    print("No matching vehicle found.")

    # Method to compute nepali dates
    @api.depends('check_in_date', 'check_out_date')
    def _compute_nepali_dates(self):
        for record in self:
            if record.check_in_date:
                check_in_nepali_date = nepali_datetime.date.from_datetime_date(record.check_in_date)
                record.check_in_date_bs = check_in_nepali_date.strftime('%Y-%m-%d')
            else:
                record.check_in_date_bs = False

            if record.check_out_date:
                check_out_nepali_date = nepali_datetime.date.from_datetime_date(record.check_out_date)
                record.check_out_date_bs = check_out_nepali_date.strftime('%Y-%m-%d')
            else:
                record.check_out_date_bs = False

            # if record.plan_date:
            #     plan_date_nepali_date = nepali_datetime.date.from_datetime_date(record.plan_date)
            #     record.plan_date_bs = plan_date_nepali_date.strftime('%Y-%m-%d')
            # else:
            #     record.plan_date_bs = False

    # Method to compute check in time
    @api.depends('check_in_time_unformatted')
    def _compute_check_in_time(self):
        # print("unformat check in time",self.check_in_time_unformatted)
        for record in self:
            if record.check_in_time_unformatted:
                try:
                    time_str = record.check_in_time_unformatted
                    hours, minutes = map(int, time_str.split(":"))
    
                    # Convert to decimal format
                    decimal = (hours / 24) + (minutes / 1440)
                    # print("decimal", decimal)

                    decimal_time = float(decimal)
                    total_seconds = int(decimal_time * 24 * 60 * 60)
                    hours = (total_seconds // 3600) % 24
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60

                    record.check_in_time = f"{hours:02}:{minutes:02}:{seconds:02}"
                    # print("check in time", record.check_in_time)
                except ValueError:
                    record.check_in_time = ''
            else:
                record.check_in_time = ''

    # Method to compute check out time
    @api.depends('check_out_time_unformatted')
    def _compute_check_out_time(self):

        # print("unformat check out time ")
        for record in self:
            if record.check_out_time_unformatted:
                try:
                    time_str = record.check_out_time_unformatted
                    hours, minutes = map(int, time_str.split(":"))
                    decimal = (hours / 24) + (minutes / 1440)
                    # print("decimal", decimal)

                    decimal_time = float(decimal)
                    total_seconds = int(decimal_time * 24 * 60 * 60)
                    hours = (total_seconds // 3600) % 24
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60

                    record.check_out_time = f"{hours:02}:{minutes:02}:{seconds:02}"
                    # print("check out time", record.check_out_time)
                except ValueError:
                    record.check_out_time = ''
            else:
                record.check_out_time = ''

    # Method to check vehicle selection
    @api.constrains('two_wheeler', 'four_wheeler', 'heavy')
    def _check_vehicle_selection(self):
        for record in self:
            selected_categories = []
            
            if record.two_wheeler:
                selected_categories.append("2 Wheeler")
            if record.four_wheeler:
                selected_categories.append("4 Wheeler")
            if record.heavy:
                selected_categories.append("Heavy Vehicle")
            if len(selected_categories) > 1:
                raise ValidationError(
                    f"Only one vehicle category can be selected at a time among: {', '.join(selected_categories)}."
                )

    # type_of_payment = fields.Char(string="Payment Type")
    
    # def action_register_payments(self):  
    #     """Method for viewing the wizard for register payment"""
    #     view_id = self.env.ref('agriculture_market_place.register_payment_wizard_view_form').id
    #     return {
    #         'name': 'Register Payment',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',
    #         'res_model': 'register.payment.wizard',
    #         'views': [(view_id, 'form')],
    #         'context': {
    #             'default_parking_duration': self.duration,
    #             'default_amount': self.parking_cost,
    #             'default_ref': self.final_number,
    #             'active_id': self.id, 
    #         },
    #         'target': 'new',
    #     }

   
    # Method to compute final number
    @api.depends('zonal_code', 'lot_number', 'vehicle_number', 'custom_number','vehicle_system',
    'province_code','vehicle_code','province_number','electric_vehicle_num')
    def _compute_final_number(self):
        # print("#######################################",self.electric_vehicle_num)
        for record in self:
            if record.electric_vehicle_num:
                record.final_number = self.electric_vehicle_num
            else:
                if record.vehicle_system == 'old':
                    parts = [
                        record.zonal_code or '',
                        record.lot_number or '',
                        record.vehicle_number or '',
                        record.custom_number or ''
                    ]
                    record.final_number = '-'.join(filter(bool, parts))

                elif record.vehicle_system == 'new':
                    parts = [
                        record.province_code or '',
                        record.vehicle_code or '',
                        record.vehicle_number or '',
                        record.province_number or '',
                        record.custom_number or ''
                    ]
                    record.final_number = '-'.join(filter(bool, parts))
                elif record.vehicle_system == 'pradesh':
                    parts = [
                        record.province_code or '',
                        record.office_code or '',
                        record.lot_number or '',
                        record.vehicle_number or '',
                        record.custom_number or ''
                    ]
                    record.final_number = '-'.join(filter(bool, parts))
                else:
                    record.final_number = self.default_vehicle_number

    # Method to handle vehicle system
    @api.onchange('vehicle_system')
    def _onchange_oldnew_type(self):
       
        if self.vehicle_system == 'old':
            # self.vehicle_state = 'old'
            self.province = ''
            self.heavy = ''
            self.two_wheeler = ''
            self.four_wheeler = ''
            self.province_number = ''
            self.custom_number=''
            self.province_code=''
            self.vehicle_code=''
        elif self.vehicle_system == 'new':
            # self.vehicle_state = 'new'
            self.vehicle_number = ''
            self.vehicle_type = ''
            self.vehicle_classification = ''
            self.custom_number=''
        else:
            self.province = ''
            self.heavy = ''
            self.two_wheeler = ''
            self.four_wheeler = ''
            self.province_number = ''
            self.custom_number=''
            self.province_code=''
            self.vehicle_code=''
            self.vehicle_number = ''
            self.vehicle_type = ''
            self.vehicle_classification = ''
            self.custom_number=''
            self.lot_number=''
            self.zonal_id=''
            self.zonal_code =''

    # Method to handle vehicle type
    @api.onchange('vehicle_type','vehicle_classification','two_wheeler','four_wheeler','heavy')
    def _onchange_vehicle_type(self):

        if self.vehicle_type and self.vehicle_classification:
            vehicle_class = self.vehicle_classification
            
            vehicle_record = self.env['vehicle.old.classification'].sudo().search([
                ('v_type', '=', self.vehicle_type.vehicle_type),
                ('name', '=', vehicle_class)
            ], limit=1)
        
            if vehicle_record:     
                # self.old_id = vehicle_record.id
                self.vehicle_number = f"{vehicle_record.code}"

        
        if self.two_wheeler: 
            two_wheeler = self.two_wheeler
            vehicle_record = self.env['vehicle.new.classification'].sudo().search([
                ('v_type', '=', '2_wheeler'),
                ('name', '=',two_wheeler)
            ], limit=1)

            if vehicle_record:
                self.vehicle_code = f"{vehicle_record.code}"

        elif self.four_wheeler:                               
            vehicle_record = self.env['vehicle.new.classification'].sudo().search([
                ('v_type', '=', '4_wheeler'),
                ('name', '=', self.four_wheeler)
            ], limit=1)
            if vehicle_record:

                self.vehicle_code = f"{vehicle_record.code}"
        elif self.heavy:
            vehicle_record = self.env['vehicle.new.classification'].sudo().search([
                ('v_type', '=', 'heavy'),
                ('name', '=', self.heavy)
            ], limit=1)
            if vehicle_record:
                self.vehicle_code = f"{vehicle_record.code}"
        return {}

    # Method to handle zonal id
    @api.onchange('zonal_id')
    def _onchange_zonal_id(self):
        if self.zonal_id:
            self.zonal_code = self.zonal_id.code
        return {}
    
    # Method to handle province
    @api.onchange('province')
    def _onchange_province_id(self):
        if self.province:
            self.province_code = self.province.name.split()[0]
        return {}
            
    # Method to compute duration
    @api.depends('check_out_time', 'check_in_time', 'check_out_date', 'check_in_date')
    def _compute_duration(self):
        # print("computing duration,,,,,,,,,,,,,,,,,,,")
        for rec in self:
            if rec.check_in_time and rec.check_out_time and rec.check_in_date and rec.check_out_date:
                check_in_time = self._str_to_time(rec.check_in_time)
                check_out_time = self._str_to_time(rec.check_out_time)

                if check_in_time and check_out_time:
                    check_in_datetime = datetime.combine(rec.check_in_date, check_in_time)
                    check_out_datetime = datetime.combine(rec.check_out_date, check_out_time)

                    # Handle overnight shifts
                    if check_out_datetime < check_in_datetime:
                        check_out_datetime += timedelta(days=1)

                    duration_seconds = (check_out_datetime - check_in_datetime).total_seconds()

                    rec.hours = int(duration_seconds // 3600)
                    rec.minutes = int((duration_seconds % 3600) // 60)
                    rec.seconds = int(duration_seconds % 60)

                    total_hours = rec.hours + rec.minutes / 60.0 + rec.seconds / 3600.0
                    rec.duration = total_hours
                else:
                    rec.duration = 0.0
                    rec.hours = 0
                    rec.minutes = 0
                    rec.seconds = 0
            else:
                rec.duration = 0.0
                rec.hours = 0
                rec.minutes = 0
                rec.seconds = 0

            if self.vehicle_type and self.vehicle_type.cost_per_hour:
                self.parking_cost = self.duration * self.vehicle_type.cost_per_hour

    # Method to compute fine
    @api.depends('duration', 'vehicle_type.time_duration', 'vehicle_type.fine_amount')
    def _compute_fine_cost(self):
        for rec in self:
            if rec.duration > rec.vehicle_type.time_duration:
                extra_time = rec.duration - rec.vehicle_type.time_duration
                rec.fine_cost = extra_time * rec.vehicle_type.fine_amount
            else:
                rec.fine_cost = 0  # No fine if duration is within the allowed time
    
    # Method to compute total cost
    @api.depends('parking_cost', 'fine_cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.parking_cost + rec.fine_cost

    # Method to convert string to time
    def _float_to_time(self, float_time):
        parts = float_time.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2]) if len(parts) > 2 else 0
        return time(hours, minutes, seconds)

    # Method to handle vehicle number
    @api.depends('number')
    def change_vehicle_number(self):
        if not self.number:
            return {} 
        parts = self.number.split('-')
   
        
        if len(parts) < 4:
            return {}  
     
        def get_vehicle_type(vehicle_number):
            vehicle_type_record = self.env['vehicle.old.classification'].search([('code', '=', vehicle_number)], limit=1)
            if vehicle_type_record:
                vehicle_type = self.env['custom.vehicle.type'].search([('vehicle_type', '=', vehicle_type_record.v_type)], limit=1)
                return vehicle_type_record, vehicle_type
            return None, None

        # Handle the first case (if zonal_code length is 2)
        if len(parts[0]) == 2:
            zonal_code = parts[0]
            if len(zonal_code) == 2:  # Ensure valid zonal code length
                self.lot_number = parts[1]
                vehicle_number = parts[2]

                # Set zonal_code
                self.zonal_code = zonal_code

                # Get vehicle type details
                vehicle_type_record, vehicle_type = get_vehicle_type(vehicle_number)

                if vehicle_type_record and vehicle_type:
                    self.vehicle_classification = vehicle_type_record.name
                    self.vehicle_type = vehicle_type.id
                    self.vehicle_number = vehicle_number
                    self.custom_number = parts[3]
                    self.vehicle_system = "old"
            return {}

        # Handle the second case (if parts have 5 elements)
        if len(parts) == 5:
            pradesh = parts[4]
            zonal_code = parts[0]

            if pradesh:
                self.vehicle_system = "pradesh"
                if zonal_code == 'Sudur':
                    province = 'Sudur Paschim Province'
                else:
                    province = zonal_code + " Province"
                province_value = self.env['location.province'].search([('name', '=', province)], limit=1)
                self.province = province_value.id
                self.province_code = zonal_code
                self.office_code = parts[1]
                self.lot_number = parts[2]

                vehicle_number = parts[3]

                # Get vehicle type details for pradesh
                vehicle_type_record, vehicle_type = get_vehicle_type(vehicle_number)

                if vehicle_type_record and vehicle_type:
                    self.vehicle_classification = vehicle_type_record.name
                    self.vehicle_type = vehicle_type.id
                    self.vehicle_number = vehicle_number
                    self.custom_number = parts[4]

        elif len(parts) == 4:
            zonal_code = parts[0]
           
            self.vehicle_system = "new"
            if zonal_code == 'Sudur':
                province = 'Sudur Paschim Province'
            else:
                province = zonal_code + " Province"
            province_value = self.env['location.province'].search([('name', '=', province)], limit=1)
            self.province = province_value.id
            self.province_code = zonal_code
            vehicle_code = parts[1]
            vehicle_record = self.env['vehicle.new.classification'].search([('code', '=', vehicle_code)], limit=1)

            self.province_number = parts[2]
            self.custom_number = parts[3]
            self.vehicle_code = vehicle_code

            if vehicle_record:
                heavy_values = dict(self._fields['heavy'].selection)
                two_wheeler_values = dict(self._fields['two_wheeler'].selection)
                four_wheeler_values = dict(self._fields['four_wheeler'].selection)

                # Assign vehicle classification based on type
                if vehicle_record.name in heavy_values:
                    self.heavy = vehicle_record.name
                elif vehicle_record.name in two_wheeler_values:
                    self.two_wheeler = vehicle_record.name
                elif vehicle_record.name in four_wheeler_values:
                    self.four_wheeler = vehicle_record.name

        return {}



    # @api.depends('zonal_id')
    # def change_zonal_id(self):
    #     if self.zonal_id:
    #         self.zonal_code = self.zonal_id.code
    #     return {}

    # @api.depends('province')
    # def change_province_id(self):
    #     if self.province:
    #         self.province_code = self.province.name.split()[0]
    #     return {}

    # @api.depends('vehicle_type','vehicle_classification')
    # def change_vehicle_type(self):

    #     if self.vehicle_type and self.vehicle_classification:
    #         vehicle_class = self.vehicle_classification
            
    #         vehicle_record = self.env['vehicle.old.classification'].sudo().search([
    #             ('v_type', '=', self.vehicle_type.vehicle_type),
    #             ('name', '=', vehicle_class)
    #         ], limit=1)
        
    #         if vehicle_record:     
    #             # self.old_id = vehicle_record.id
    #             self.vehicle_number = f"{vehicle_record.code}"

        
    #     if self.two_wheeler: 
    #         two_wheeler = self.two_wheeler
    #         vehicle_record = self.env['vehicle.new.classification'].sudo().search([
    #             ('v_type', '=', '2_wheeler'),
    #             ('name', '=',two_wheeler)
    #         ], limit=1)

    #         if vehicle_record:
    #             self.vehicle_code = f"{vehicle_record.code}"

    #     elif self.four_wheeler:                               
    #         vehicle_record = self.env['vehicle.new.classification'].sudo().search([
    #             ('v_type', '=', '4_wheeler'),
    #             ('name', '=', self.four_wheeler)
    #         ], limit=1)
    #         if vehicle_record:

    #             self.vehicle_code = f"{vehicle_record.code}"
    #     elif self.heavy:
    #         vehicle_record = self.env['vehicle.new.classification'].sudo().search([
    #             ('v_type', '=', 'heavy'),
    #             ('name', '=', self.heavy)
    #         ], limit=1)
    #         if vehicle_record:
    #             self.vehicle_code = f"{vehicle_record.code}"
    #     return {}
    
    # Check In Method
    def action_check_in(self):
        """Method for checking in"""
     
        existing_vehicle_record = self.env['vehicle.number'].sudo().search([
            ('final_number', '=', self.final_number),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'check_in'),
        ], limit=1)

        if existing_vehicle_record:
            raise ValidationError(_(
                "The vehicle with number '%s' is already checked in. Please ensure it has checked out before checking in again."
            ) % self.final_number)
        self.state = 'check_in'
        self.check_in_bool = True 
        self.check_out_bool = False
        current_time = datetime.now(timezone('Asia/Kathmandu'))
        self.check_in_time = current_time.strftime('%H:%M:%S')
        self.check_in_date = fields.Date.context_today(self)
        # self.check_in_date_bs = nepali_datetime.date.from_datetime_date(self.check_in_date)
        self.arrival_date = fields.Date.context_today(self)
        self.arrival_date_bs = nepali_datetime.date.from_datetime_date(self.arrival_date)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',  
        }

    # Check Out Method
    def action_check_out(self):
        """Method for checking out"""
        existing_vehicle_number = self.env['vehicle.number'].sudo().search([
            ('final_number', '=', self.final_number),
            ('company_id', '=', self.company_id.id),
             ('state', '=', 'check_out'),
        ], limit=1)

        if existing_vehicle_number  :
            raise ValidationError((
                "The vehicle with number '%s' is already checked out. Please ensure it has checked out before checking out again."
            ) % self.final_number)
        self.state = 'check_out'
        existing_vehicle_number.state=self.state
        self.check_out_bool = True
        self.check_in_bool = False
        self.check_out_date =  fields.Date.context_today(self)
        
        # existing_vehicle_number.date_bs = self.check_out_date_bs
        current_time = datetime.now(timezone('Asia/Kathmandu'))
        self.check_out_time = current_time.strftime('%H:%M:%S')  
        self._compute_duration()
        existing_vehicle_number.duration = self.duration
        existing_vehicle_number.hours = self.hours
        existing_vehicle_number.minutes = self.minutes
        existing_vehicle_number.seconds = self.seconds

        if self.vehicle_type and self.vehicle_type.cost_per_hour:
            self.parking_cost = self.duration * self.vehicle_type.cost_per_hour

        return {
            'type': 'ir.actions.client',
            'tag': 'reload', 
        }

    # Method for checking the check_in_date and check_out_date
    @api.constrains('check_in_date','check_out_date')
    def _check_check_in_date(self):
        if self.check_in_date and self.check_in_date > fields.Date.today():
            raise ValidationError("Check In Date cannot be in the future.")

        if self.check_out_date and self.check_out_date < self.check_in_date:
            raise ValidationError("Check Out Date cannot be ahead of Check In Date.")
    # def action_register_payments(self):  
    #     """Method for viewing the wizard for register payment"""
    #     view_id = self.env.ref('agriculture_market_place.register_payment_wizard_view_form').id
    #     return {
    #         'name': 'Register Payment',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',
    #         'res_model': 'register.payment.wizard',
    #         'views': [(view_id, 'form')],
    #         'context': {
    #             'default_parking_duration': self.duration,
    #             'default_amount': self.parking_cost,
    #             'default_ref': self.final_number,
    #             'active_id': self.id, 
    #         },
    #         'target': 'new',
    #     }
    
    # def renew_bluebook(self):
    #     pass


class AssignRoute(models.Model):
    _name = 'data.route'
    _description ='Route Data'
    _rec_name = 'name'

    name = fields.Char('Route Name', required=True)
    source = fields.Char('Source Location', required=True)
    destination = fields.Char('Destination Location', required=True)
    route_length = fields.Float('Route Length (km)')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

class InheritIrModel(models.Model):
    _inherit = 'ir.model'
    _description ='Inherit Model'
   
class InheirtIrmodelFields(models.Model):
    _inherit = 'ir.model.fields'
    _description ='Inherit Model Fields'
   
class FleetRoute(models.Model):
    _name = 'fleet.route'
    _description = 'Route Model'
    
    name = fields.Many2one('data.route',string='Route Name', required=True)
    source = fields.Char('Start Location', required=True,related='name.source')
    destination = fields.Char('Destination Location', required=True, related='name.destination')
    vehicle_number = fields.Many2one('vehicle.number',string='Vehicle Number')
    checkpoints = fields.One2many('fleet.route.checkpoint', 'route_id', string='Checkpoints')
    route_length = fields.Float('Route Length (km)',related='name.route_length')
    route_date = fields.Date(string='From Date')
    route_date_bs = fields.Char(string= 'Route Date(BS)',compute='_compute_nepali_dates', store=True)

    route_date_to = fields.Date(string='To Date')
    route_date_to_bs = fields.Char(string= 'Route Date To(BS)',compute='_compute_nepali_dates', store=True)
    total_days = fields.Char("Total Days:",store= True,compute='_compute_total_days',readonly=False)

    purpose = fields.Text(string="Purpose Of Travel")

    route_time_from = fields.Char('Route Time From:')
    route_time_to = fields.Char('Route Time To:')
    remarks = fields.Text('Remarks')
    total_hours = fields.Char("Total Hours:",store= True,compute='_compute_total_hours',readonly=False)
    # estimated_time = fields.Float('Estimated Time (hours)')

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    

    @api.depends('route_date', 'route_date_to')
    def _compute_total_days(self):
        for record in self:
            if not record.route_date:
                record.route_date = datetime.today()  
            if not record.route_date_to:
                record.route_date_to = datetime.today()     
            if record.route_date_to < record.route_date:
                raise ValidationError("End date cannot be earlier than the start date.")
            else:
                total_days = (record.route_date_to - record.route_date).days
                record.total_days = str(total_days) 
    @api.depends('route_time_from', 'route_time_to')
    def _compute_total_hours(self):
        for record in self:
            if record.route_time_from and record.route_time_to:
                start_hr = int(round(float(record.route_time_from), 2))
                start_min = int(((round(float(record.route_time_from), 2)) - start_hr)* 100)
                format_start = f"{start_hr}:{start_min:02d}"

                end_hr = int(round(float(record.route_time_to), 2))
                end_min = int(((round(float(record.route_time_to), 2)) - end_hr)* 100)
                format_end = f"{end_hr}:{end_min:02d}"

                try:
                    time_from = datetime.strptime(format_start, '%H:%M')
                    time_to = datetime.strptime(format_end, '%H:%M')
                    
                    if time_to < time_from:
                      
                        time_to += timedelta(days=1)
                    
                    duration = time_to - time_from
                    total_seconds = duration.total_seconds()
              
                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
        
                    record.total_hours = f"{hours:02d}:{minutes:02d}"
                except ValueError:
                    record.total_hours = "Invalid Time Format"
            else:
                record.total_hours = "00:00"

    @api.depends('route_date')
    def _compute_nepali_dates(self):
        for record in self:
            if record.route_date:
                route__nepali_date = nepali_datetime.date.from_datetime_date(record.route_date)
                record.route_date_bs = route__nepali_date.strftime('%Y-%m-%d')
            else:
                record.route_date_bs = False
                
class FleetRouteCheckpoint(models.Model):
    _name = 'fleet.route.checkpoint'
    _description = 'Route Checkpoint'
    
    name = fields.Char('Checkpoint Name', required=True)
    sequence = fields.Integer('Checkpoint Sequence', required=True)
    route_id = fields.Many2one('fleet.route', string='Route')
    location = fields.Char('Location')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
