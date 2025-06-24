# models/transport_assignment.py
from odoo import models, fields, api
from ..models.transport_order import convert_to_bs_date
from ..utils.dashboard_notification import DutyAllocationNotifier
from datetime import time, datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import _
from odoo.exceptions import ValidationError, UserError
import nepali_datetime
from ..models.mailsender import MailSender

from ..utils.dashboard_notification import notify_transport

class InheritCheckPoints(models.Model):
    _inherit = 'fleet.route.checkpoint'
    
    duties_id = fields.Many2one("transport.assignment", string="Duty") 
    
class TransportAssignment(models.Model):
    _name = 'transport.assignment'
    _description = 'Transport Assignment'
    _order = 'create_date desc'
    _rec_name = 'code'

    # Auto-generated code field
    code = fields.Char(
        string='Assignment Code',
        copy=False,
        readonly=True,
        default='New'
    )

    # Link to the related transport order
    order_id = fields.Many2one(
        'transport.order', string='Order Id', required=True, ondelete='cascade'
    )

    # Assigned vehicle for the transport
    vehicle_id = fields.Many2one(
        'vehicle.number', 
        string='Vehicle',
        domain=[
            ('available', '=', True),
            '|',
            ('heavy', 'in', ['truck', 'mini_truck']),
            ('vehicle_type.vehicle_type', '=', 'heavy'),
        ],
        required=True,
    )

    # Assigned driver for the transport
    driver_id = fields.Many2one(
        'driver.details', string='Driver',
        domain=[('available','=',True)]
    )
    helper_id = fields.Many2one('helper.details', string='Helper')
    
    # Date when the assignment was made
    assigned_date = fields.Date(
        string='Assigned Date', default=fields.Datetime.now
    )
    from_date = fields.Date(string="Pickup Date",related='order_id.scheduled_date_from')
    to_date = fields.Date(string="Delivery Date", related='order_id.scheduled_date_to')
    from_date_bs = fields.Char(string="From Date BS", compute="_compute_date_bs")
    to_date_bs = fields.Char(string="To Date BS", compute="_compute_date_bs")
    # Assigned date in Nepali Bikram Sambat format (computed)
    assigned_date_bs = fields.Char(
        string='Assigned Date BS', compute='_compute_date_bs'
    )

    # Encoded polyline string for route tracking or mapping
    route_polyline = fields.Text(string='Route Polyline')

    # Raw GPS integration data or JSON for tracking/logging
    gps_data = fields.Text(string='GPS Integration Data')
    
    route_data = fields.Many2one("data.route", string="Route Name")
    source_location = fields.Char(string="Source Location:",related = "route_data.source",store=True)
    source_address = fields.Text(string="Source Location:", _compute = "_compute_source_address",store=True)
    
    destination_location = fields.Char(string="Destination Location:", related="route_data.destination", store=True)
    destination_address = fields.Text(string="Source Location:", _compute = "_compute_destination_address",store=True)
    route_length = fields.Float(related='route_data.route_length',string="Route Length",store=True)
    
    
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
    
    checkpoints_details = fields.One2many('fleet.route.checkpoint', 'duties_id',string="CheckPoints")
    
    
    
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

    @api.depends('route_date','route_date_to')
    def _compute_nepali_dates(self):
        for record in self:
            if record.route_date:
                route__nepali_date = nepali_datetime.date.from_datetime_date(record.route_date)
                record.route_date_bs = route__nepali_date.strftime('%Y-%m-%d')
            else:
                record.route_date_bs = False
            if record.route_date_to:
                route_to_nepali_date = nepali_datetime.date.from_datetime_date(record.route_date_to)
                record.route_date_to_bs = route_to_nepali_date.strftime('%Y-%m-%d')
            else:
                record.route_date_to_bs = False
                
    @api.onchange('route_data')
    def _compute_source_address(self):
       if self.route_data:
            # SQL Join Query to concatenate fields from related models
            query = """
                SELECT 
                    lp.name, 
                    rd.district_name, 
                    rp.palika_name,
                    dr.source_ward
                FROM data_route AS dr
                LEFT JOIN location_province AS lp ON lp.id = dr.source_province
                LEFT JOIN location_district AS rd ON rd.id = dr.source_district
                LEFT JOIN location_palika AS rp ON rp.id = dr.source_palika
                WHERE dr.id = %s
            """
            self.env.cr.execute(query, (self.route_data.id,))
            result = self.env.cr.fetchone()
            if result:
                province_name, district_name, palika_name, ward_name = result
                self.source_address = f"{province_name},{district_name},{palika_name},{ward_name}"
            
    @api.onchange('route_data')
    def _compute_destination_address(self):
        if self.route_data:
            route = self.route_data
            source_province = route.source_province.name if route.source_province else ''
            source_district = route.source_district.district_name if route.source_district else ''
            source_palika = route.source_palika.palika_name if route.source_palika else ''
            source_ward = route.source_ward if route.source_ward else ''
            self.destination_address = f"{source_province},{source_district},{source_palika},{source_ward}"    
                
    @api.depends('assigned_date','to_date','from_date')
    def _compute_date_bs(self):
        # Convert Gregorian date to Bikram Sambat format
        for record in self:
            record.assigned_date_bs = convert_to_bs_date(record.assigned_date) if record.assigned_date else False
            record.from_date_bs = convert_to_bs_date(record.from_date) if record.from_date else False
            record.to_date_bs = convert_to_bs_date(record.to_date) if record.to_date else False
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        """Automatically load driver and fuel type from the selected vehicle."""
        if self.vehicle_id:
            self.driver_id = self.vehicle_id.driver_id
            self.order_id.assigned_truck_id = self.vehicle_id
        else:
            self.driver_id = False
    
    def _generate_assignment_code(self):
        """Generate unique code 'Assignment/001', 'Assignment/002', …"""
        last = self.search([], order='id desc', limit=1)
        if last and last.code and '/' in last.code:
            try:
                num = int(last.code.split('/')[-1]) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        return f"Assignment/{num:05d}"
    
    def send_notification(self, duty_id=None):
        customer_name    = self.order_id.customer_name.name if self.order_id else 'N/A'
        driver_name      = self.driver_id.name if self.driver_id else 'N/A'
        vehicle_number   = self.vehicle_id.final_number if self.vehicle_id else 'N/A'
        from_date        = self.order_id.request_id.estimated_pickup_date or 'N/A'
        to_date          = self.order_id.request_id.estimated_delivery_date or 'N/A'
        pickup_address   = self.order_id.pickup_location or 'N/A'
        delivery_address = self.order_id.delivery_location or 'N/A'

        notify_transport(
            env=self.env,
            notification_type='duty_allocation',
            customer_name = customer_name,
            driver_name=driver_name,
            vehicle_number=vehicle_number,
            from_date=from_date,
            to_date=to_date,
            pickup_location=pickup_address,
            delivery_location=delivery_address,
            duty_id=duty_id
        )

        # Send email notification
        if self.driver_id and self.driver_id.email:
            self._send_duty_allocation_email(
                self.driver_id.email,
                customer_name,
                driver_name,
                vehicle_number,
                from_date,
                to_date,
                pickup_address,
                delivery_address
            )

    def createRecord(self, assignment):
        print("Calling createRecord for assignment ID %s", assignment.id)
        print("Assignment",assignment.vehicle_id.id,assignment.route_data.id,self.vehicle_id.id,assignment.order_id.delivery_location,)
        if assignment.route_data:
            route = self.env['fleet.route'].with_context(skip_duty_allocation=True).create({
                'vehicle_number':assignment.vehicle_id.id,
                'driver_id': assignment.driver_id.id,
                'name':assignment.route_data.id,
                'route_time_from':assignment.route_time_from,
                'route_time_to':assignment.route_time_to,
                'route_date':assignment.route_date,
                'route_date_to':assignment.route_date_to,
                'purpose':assignment.purpose,
                'remarks':assignment.remarks,
                'checkpoints': [(6, 0, assignment.checkpoints_details.ids)]

            })
            # Create duty allocation
            if route and assignment.driver_id and assignment.vehicle_id and assignment.order_id:
                self.env['duty.allocation'].create({
                    'duty_name': "Transport Duty",
                    'driver_id': assignment.driver_id.id,
                    'vehicle_id': assignment.vehicle_id.id,
                    'pickup_location': assignment.order_id.pickup_location,
                    'pickup_address': assignment.order_id.pickup_address,
                    'delivery_location': assignment.order_id.delivery_location,
                    'delivery_address': assignment.order_id.delivery_address,
                    'from_date': assignment.route_date,
                    'to_date': assignment.route_date_to,
                    'customer_phone': assignment.order_id.customer_name.phone,
                    'transport_order': assignment.order_id.name,
                    'pickup_date':assignment.from_date,
                    'delivery_date':assignment.to_date,
                    'route_name':route.id,
                })
                
    
    def _send_duty_allocation_email(self, driver_email, customer_name, driver_name, vehicle_number, 
                              from_date, to_date, pickup_address, delivery_address):
        """Send duty allocation email to driver"""
        print("Sending duty allocation email to:", driver_email)
        if driver_email:
            try:
                mail_sender = MailSender(self.env)
                body_html = f'''
                    <p>Dear {driver_name},</p>
                    <p>You have been assigned a new transport duty with the following details:</p>
                    <p><strong>Customer:</strong> {customer_name}</p>
                    <p><strong>Vehicle Number:</strong> {vehicle_number}</p>
                    <p><strong>From Date:</strong> {from_date}</p>
                    <p><strong>To Date:</strong> {to_date}</p>
                    <p><strong>Pickup Location:</strong> {pickup_address}</p>
                    <p><strong>Delivery Location:</strong> {delivery_address}</p>
                    <p>Please check your duties in the system.</p>
                    <p>Thank you!</p>
                '''
                
                mail_sender.send_mail(
                    email_to=driver_email,
                    subject='New Duty Allocation',
                    body_html=body_html,
                    model='transport.assignment',
                    res_id=self.id
                )
                print("Email sent successfully to:", driver_email)
            except Exception as e:
                print(f"Error sending email: {e}")
        else:
            print("Email sending skipped: Email address is not available for the driver.")
            raise UserError("Email address is not available for the driver.")
    
    @api.model
    def create(self, vals):
        # fill code if new
        if vals.get('code', 'New') == 'New':
            vals['code'] = self._generate_assignment_code()
        assignment = super().create(vals)
        print("#####################################",assignment.id)
        # Write the assignment id to manifest after searching the manifest and has same order_id
        if assignment.order_id:
            # print("assignment.order_id", assignment.order_id)
            duty = assignment.createRecord(assignment)
            if duty:
                assignment.send_notification(duty_id=duty.id if duty else None) 
            assignment.send_notification(duty_id=duty.id if duty else None)
            # send sms to driver regarding duty allocation
            # sms_service = self.env['sparrow.sms']
            # if assignment.driver_id and assignment.driver_id.emergency_contact:
            #     receiver_emergency_contact = assignment.driver_id.emergency_contact
            #     print("Sending SMS to driver:", receiver_emergency_contact)
            #     message = f"Dear {assignment.driver_id.name}, you have been assigned a transport duty for order {assignment.order_id.name}. Please check your Odoo app for details."
            #     print("Message:", message)
            #     sms_service.send_sms(receiver_emergency_contact, message)
            #     print("SMS sent successfully to driver:", receiver_emergency_contact)
            manifests = self.env['transport.manifest'].search([(
                'order_id', '=', assignment.order_id.id
            )])
            # print("manifests", manifests)
            for manifest in manifests:
                manifest.write({'assignment_id': assignment.id})

        # Update the transport order with assigned truck
        if assignment.vehicle_id and assignment.order_id:
            assignment.order_id.write({'assigned_truck_id': assignment.vehicle_id.id})

        return assignment

    def write(self, vals):
        result = super(TransportAssignment, self).write(vals)
        # print("Inside write", vals)
        # Write the assignment id to manifest after searching the manifest and has same order_id
        if self.order_id:
            manifests = self.env['transport.manifest'].search([(
                'order_id', '=', self.order_id.id
            )])
            # print("manifests", manifests)
            for manifest in manifests:
                manifest.write({'assignment_id': self.id})

        # If the vehicle is being updated on an existing assignment record, update the related transport order
        if 'vehicle_id' in vals:
            for record in self:
                if record.order_id and record.vehicle_id:
                    record.order_id.write({'assigned_truck_id': record.vehicle_id.id})
        return result
    
    
    
class ExistingAssignment(models.Model):
    _name = 'existing.assignment'
    _description = 'Assign to already assigned vehicle'
    
    order_id = fields.Many2one(
        'transport.order', string='Transport Order', required=True, ondelete='cascade'
    )
    vehicle_id = fields.Many2one('vehicle.number',string='Vehicle Number')
    driver = fields.Many2one('driver.details',string='Driver')
    date = fields.Char(string='Date Bs')
    check_points = fields.Char(string='Check Points')
    route = fields.Many2one('fleet.route',string='Route Name')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
