from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import time, datetime, timedelta
from pytz import timezone
import nepali_datetime
from ..utils.dashboard_notification import Utilities 
import pytz
from ..models.maintenance_management import convert_to_bs_date
from odoo.exceptions import UserError
import re
from ..models.mailsender import MailSender
from odoo.addons.transport_management.utils.dashboard_notification import notify_transport


class DriverDetails(models.Model):
    _name = 'driver.details'
    _description = 'Driver Details Management'
    _sql_constraints = [('unique_helper_id', 'unique(helper_id)', 'Helper already exists')]

    name = fields.Char(string='Driver Name', required=True)
    name_np = fields.Char(string= 'Driver Name(np)')
    contact_details = fields.Text(string='Address')
    license_number = fields.Char(string='License Number')
    license_expiry_date = fields.Date(string='License Expiry Date')
    license_expiry_date_bs = fields.Char(string='License Expiry Date(BS)',compute='_compute_bs_date', store=True)
    
    emergency_contact = fields.Char(string='Contact', size=10)
    citizenship_number = fields.Char(string='Citizenship Number')
    duty_ids = fields.One2many('duty.allocation', 'driver_id', string='Duty Records')
    performance_ids = fields.One2many('driver.performance', 'driver_id', string='Performance Records')

    training_ids = fields.One2many('driver.training', 'driver_id', string='Training Records')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    available = fields.Boolean(string="Is Available ?", default=True)

    helper_id = fields.Many2one('helper.details', string='Helper')

    employee_id = fields.Many2one(
        'hr.employee',
        string='Related Employee',
        readonly=True,
        ondelete='set null',
    )
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')

    # Helper to map driver fields to employee fields
    # This is used to create an employee record when creating a driver
    DRIVER_EMPLOYEE_FIELD_MAP = {
        'name': 'name',
        'emergency_contact': 'mobile_phone',
        'company_id': 'company_id',
        'gender': 'gender',
        'job_title': 'job_title',
    }

    job_title = fields.Char(string='Job Title', default='Driver')
    email = fields.Char(string='Email')

    # Validate email format
    @api.constrains('email')
    def _check_email_format(self):
        for record in self:
            if record.email and not re.match(r"[^@]+@[^@]+\.[^@]+", record.email):
                raise ValidationError("Invalid email format.")

    @api.depends('license_expiry_date')
    def _compute_bs_date(self):
        for record in self:
            print("record.license_expiry_date",record.license_expiry_date)
            if record.license_expiry_date:
                arrival_nepali_date = nepali_datetime.date.from_datetime_date(record.license_expiry_date)
                print("arrival_nepali_date",arrival_nepali_date)
                record.license_expiry_date_bs = arrival_nepali_date.strftime('%Y-%m-%d')
            else:
                record.license_expiry_date_bs = False
                
    def sendNotifications(self):
        today = datetime.today().date()
        today_bs = nepali_datetime.date.from_datetime_date(today)
        seven_days = today_bs + timedelta(days=7)
        for record in self.search([]):
            expiry_date = nepali_datetime.date.from_datetime_date(record.license_expiry_date)
            utilities = Utilities(self.env)
            if today_bs <= expiry_date <= seven_days:
                expiry_date = record.license_expiry_date_bs
                driver = record.name
                utilities.showNotificationDashboard(date = expiry_date, vehicle_number = None,renewal_type = 'license', driver_name = driver)
            
    @api.constrains('emergency_contact')
    def _check_phone_format(self):
        """Ensures phone numbers are 10 digits and start with 97 or 98."""
        for record in self:
            if record.emergency_contact and (not record.emergency_contact.isdigit() or len(record.emergency_contact) != 10 or not record.emergency_contact.startswith(('97', '98'))):
                raise ValidationError("Phone number must be 10 digits long and start with 97 or 98.")

    # certifications = fields.Text(string='Certifications', compute='_compute_certifications')

    # @api.depends('training_ids')
    # def _compute_certifications(self):
    #     if self.training_ids:
    #         self.certifications = ', '.join(self.training_ids.mapped('training_type'))
    #     else:
    #         self.certifications = 'No certifications'

    # @api.constrains('emergency_contact')
    # def _check_emergency_contact(self):
    #     for record in self:
    #         if len(record.emergency_contact) < 10:
    #   
    # raise models.ValidationError('Emergency contact number must be at least 10 digits long')  
    @api.model
    def _generate_renewal_record(self):
        for driver in self.search([]):
            print("Generating",driver.id)
            duties = self.env['duty.allocation'].search([('driver_id','=',driver.id)],order = 'to_date desc')
            today_date =  nepali_datetime.date.from_datetime_date(fields.Date.today())
            to_date =  nepali_datetime.date.from_datetime_date(duties.to_date) if duties.to_date else None
            if duties.to_date_bs:
                if (to_date < today_date):
                    driver.available = True
                else:
                    driver.available = False
            else:
                driver.available = True
                
            training_rec = self.env['driver.training'].search([('driver_id','=',driver.id)],order = 'cert_expiry_date desc')
            driver.sendNotifications()
            for training_record in training_rec:
                if training_record.cert_expiry_date and training_record.training_completed == 'True':
                    print("Training Record",training_record.training_type)
                    date_diff = training_record.cert_expiry_date - fields.Date.today()
                    if date_diff <= timedelta(days=30):
                        self.env['driver.training'].create({
                            'driver_id': driver.id,
                            'training_completed': False,
                            'training_type': training_record.training_type,
                        })

    @api.model
    def create(self, vals):
        # 1) create driver
        driver = super().create(vals)

        # 2) build employee vals
        emp_vals = {}
        for drv_f, emp_f in self.DRIVER_EMPLOYEE_FIELD_MAP.items():
            if drv_f in vals:
                emp_vals[emp_f] = driver[drv_f]
                print("emp_vals",emp_vals)

        emp_vals.setdefault('job_title', 'Driver')
        # 3) create and link employee
        employee = self.env['hr.employee'].create(emp_vals)
        print("employee",employee)
        driver.employee_id = employee.id
        print("driver.employee_id",driver.employee_id)
        return driver

    def write(self, vals):
        # 1) write driver
        res = super().write(vals)

        # 2) propagate to employee if exists
        #    pick only those driver fields that changed and are in our map
        common_keys = set(vals.keys()) & set(self.DRIVER_EMPLOYEE_FIELD_MAP.keys())
        if common_keys:
            for driver in self.filtered('employee_id'):
                emp_vals = {}
                for drv_f in common_keys:
                    emp_field = self.DRIVER_EMPLOYEE_FIELD_MAP[drv_f]
                    emp_vals[emp_field] = driver[drv_f]
                if emp_vals:
                    driver.employee_id.write(emp_vals)
        return res
        
                    
class DutyAllocation(models.Model):
    _name = 'duty.allocation'
    _description = 'Duty Allocation Management'

    duty_name = fields.Char(string='Duty Name', required=True)
    driver_id = fields.Many2one('driver.details', string='Driver')
    vehicle_id = fields.Many2one('vehicle.number', string='Assigned Vehicle', required=True, ondelete='cascade')
    duty_allocation_date = fields.Date(string="Duty Allocation Date" ,  default = fields.Date.context_today)
    duty_allocation_date_bs = fields.Date(string="Duty Allocation Date BS:", _compute = "_compute_nepali_dates")
    from_date = fields.Date(string="Start Date:")
    to_date = fields.Date(string="End Date:")
    from_date_bs = fields.Char(string="Start Date(BS)", compute='_compute_bs_date', store=True)
    to_date_bs = fields.Char(string="End Date(BS)", compute='_compute_bs_date', store=True)
    
    shift_start = fields.Char(string='Shift Start Time')
    shift_end = fields.Char(string='Shift End Time') 
    start_time_shift = fields.Char(string='Shift Start Time')
    end_time_shift = fields.Char(string='Shift End Time') 
    total_work_hours = fields.Char(string='Total Work Hours/day', compute='_compute_work_hours',store=True)
    total_days = fields.Char(string='Total Work Days', compute='_compute_work_hours',store=True)
    rest_breaks = fields.Float(string='Rest Breaks Taken (hours)')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    pickup_location = fields.Char(string="Pickup Location")
    pickup_address = fields.Char(string="Pickup Address")
    delivery_location = fields.Char(string="Delivery Location")
    delivery_address = fields.Char(string="Delivery Address")
    
    customer_phone = fields.Char(string="Customer Contact Number:")
    transport_order = fields.Char(string="Order Name")
    pickup_date = fields.Date(string="Pickup Date:")
    delivery_date = fields.Date(string="Delivery Date:")
    
    pickup_date_bs = fields.Char(string="Pickup Date(Bs):",  compute='_compute_bs_date', store=True)
    delivery_date_bs = fields.Char(string="Delivery Date(Bs):",compute='_compute_bs_date', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('collecting','Start Collection'),
        ('collected', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
    ], string='Status', default='draft', tracking=True)
    
    
    route_name = fields.Many2one('fleet.route',string="Route Name")
    checkpoints = fields.One2many(related='route_name.checkpoints', string="Checkpoints", readonly=False)
    
    start_datetime = fields.Char(string='Start Date Time')
    delivery_datetime = fields.Char(string='Start Date Time')
    @api.depends('duty_allocation_date')
    def _compute_nepali_dates(self):
        for record in self:
            record.duty_allocation_date_bs = convert_to_bs_date(record.duty_allocation_date)
    def _reload_action(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action': 'reload_page'},
        }
    
    def _send_delivery_confirmation_email(self, delivery_id):
        """Send delivery confirmation email to customer"""
        print("Sending delivery confirmation email to:", delivery_id.customer_name.email)
        if delivery_id.customer_name.email:
            try:
                mail_sender = MailSender(self.env)
                body_html = f'''
                    <p>Dear {delivery_id.customer_name.name},</p>
                    <p>Your order {delivery_id.name} has been successfully delivered.</p>
                    <p><strong>Delivery Date:</strong> {fields.Date.today()}</p>
                    <p><strong>Delivery Time:</strong> {delivery_id.delivery_time}</p>
                    <p><strong>Delivery Location:</strong> {delivery_id.delivery_location}</p>
                    <p>Thank you for choosing our services!</p>
                '''
                
                mail_sender.send_mail(
                    email_to=delivery_id.customer_name.email,
                    subject='Order Delivery Confirmation',
                    body_html=body_html,
                    model='duty.allocation',
                    res_id=self.id
                )
                print("Email sent successfully to:", delivery_id.customer_name.email)
            except Exception as e:
                print(f"Error sending email: {e}")
        else:
            print("Email sending skipped: Email address is not available for the customer.")

    def _send_sms_notification(self, phone_number, message):
        """Send SMS notification to a phone number"""
        print("Sending SMS to:", phone_number)
        if phone_number:
            try:
                sms_service = self.env['sparrow.sms']
                result = sms_service.send_sms(message, phone_number)
                
                if result:
                    print(f"SMS sent successfully to {phone_number}")
                else:
                    print(f"Failed to send SMS to {phone_number}")
                    
            except Exception as e:
                print(f"Error sending SMS: {e}")
                
        else:
            print("Phone number is not available. Skipping SMS.")
        
    def action_confirm(self):
        kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        now_nep = datetime.now(kathmandu_tz)
        now_nep = now_nep.replace(microsecond=0)
        
        self.state = 'confirmed'
        request = self.env['transport.order'].search([('name', '=', self.transport_order)], limit=1)
        print("requested",request.name)
        if request:
            request.state = 'process'
            today_date = fields.Date.today()
            # request.update_date_bs = convert_to_bs_date(today_date)
            request.update_time = now_nep.strftime("%H:%M:%S")
        return self._reload_action()
    def start_collecting(self):
        # if self.pickup_date != fields.Date.today():
        #     raise UserError("Driver can only start collecting items on the scheduled pickup date.")
        kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        now_nep = datetime.now(kathmandu_tz)
        now_nep = now_nep.replace(microsecond=0)
        today_date = fields.Date.today()
        
        self.state = 'collecting'
        request = self.env['transport.order'].search([('name', '=', self.transport_order)], limit=1)
        request.update_time = now_nep.strftime("%H:%M:%S")
        # request.update_date_bs = convert_to_bs_date(today_date)
        self.send_notification(order_name = self.transport_order)
        mail_values = {
        'subject': 'Pickup Reminder - Driver En Route for Order %s' % request.customer_name.name,
        'body_html': (
            f'<p>Dear {request.customer_name.name},</p>'
            f'<p>This is a friendly reminder that our driver is currently on the way to pick up the items for your order <strong>{request.name}</strong>.</p>'
            f'<p>Kindly ensure that the items are ready for pickup to avoid any delays.</p>'
            f'<p><strong>Pickup Details:</strong></p>'
            f'<ul>'
            f'    <li><strong>Order Number:</strong> {request.name}</li>'
            f'    <li><strong>Pickup Location:</strong> {self.pickup_location}</li>'
            f'    <li><strong>Scheduled Pickup:</strong> {self.pickup_date}</li>'
            f'</ul>'
            f'<p>If you have any questions or need to reschedule, please contact us as soon as possible.</p>'
            f'<p>Thank you for your cooperation.</p>'
            f'<p>Best regards,</p>'
            f'<p>{self.env.company.name}</p>'
        ),
            'email_to': request.customer_name.email,
            'model': 'duty.allocation',
            'res_id': self.id,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send() 
        return self._reload_action()
    def action_pickup(self):
        self.state = 'collected'
        kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        now_nep = datetime.now(kathmandu_tz)
        now_nep = now_nep.replace(microsecond=0)
        transport_order = self.env['transport.order'].search([('name', '=', self.transport_order)], limit=1)
        transport_order.update_time = now_nep.strftime("%H:%M:%S")
        today_date = fields.Date.today()
        # transport_order.update_date_bs = convert_to_bs_date(today_date)
        return self._reload_action()

    def action_start_trip(self):
        kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        print("timezone", kathmandu_tz)
        now_nep = datetime.now(kathmandu_tz)
        now_nep = now_nep.replace(microsecond=0)
        
        if now_nep.tzinfo is not None:
            now_nep = now_nep.replace(tzinfo=None)
        date = now_nep.date()
        nepali_date = nepali_datetime.date.from_datetime_date(date).strftime('%Y-%m-%d')
        start_datetime = datetime.combine(datetime.strptime(nepali_date, '%Y-%m-%d').date(), now_nep.time())
                    
        self.start_datetime = start_datetime
        print("now_nep", now_nep)
        self.state = 'in_transit'
        transport_order = self.env['transport.order'].search([('name', '=', self.transport_order)], limit=1)
        if transport_order:
            today_date = fields.Date.today()
            # transport_order.update_date_bs = convert_to_bs_date(today_date)
            transport_order.state = 'in_transit'
            transport_order.pickup_time = now_nep.strftime("%H:%M:%S")
            transport_order.update_time = now_nep.strftime("%H:%M:%S")
            transport_order.scheduled_date_from = fields.Date.today()
          
            transport_order.request_id.pickup_date = fields.Date.today()

            transport_order.request_line_id.state = 'in_transit'
            transport_order.dispatched_date = nepali_datetime.date.from_datetime_date(fields.Date.today()).strftime('%Y-%m-%d')
            
        mail_values = {
        'subject': 'Delivery in Progress - Order %s' % transport_order.customer_name.name,
        'body_html': (
            f'<p>Dear {transport_order.customer_name.name},</p>'
            f'<p>We are pleased to inform you that the delivery trip for your order <strong>{transport_order.name}</strong> has started.</p>'
            f'<p>Your items are currently on the way to the delivery address.</p>'
            f'<p><strong>Delivery Details:</strong></p>'
            f'<ul>'
            f'    <li><strong>Order Number:</strong> {transport_order.name}</li>'
            f'    <li><strong>Delivery Location:</strong> {self.delivery_location}</li>'
            # f'    <li><strong>Estimated Arrival Time:</strong> [Insert ETA or use self.eta if available]</li>'
            f'</ul>'
            f'<p>You will receive another notification once the delivery has been completed.</p>'
            f'<p>Thank you for choosing our service.</p>'
            f'<p>Best regards,</p>'
            f'<p>{self.env.company.name}</p>'
        ),
        'email_to': transport_order.customer_name.email,
        'model': 'duty.allocation',  # Or the relevant model, if different
        'res_id': self.id,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send() 
        return self._reload_action()

    def action_deliver(self):
        delivery_id = self.env['transport.order'].search([('name', '=', self.transport_order)], limit=1)
        kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        print("timezone", kathmandu_tz)
        now_nep = datetime.now(kathmandu_tz)
        now_nep = now_nep.replace(microsecond=0)
        if now_nep.tzinfo is not None:
            now_nep = now_nep.replace(tzinfo=None)
        date = now_nep.date()
        nepali_date = nepali_datetime.date.from_datetime_date(date).strftime('%Y-%m-%d')
        delivery_datetime = datetime.combine(datetime.strptime(nepali_date, '%Y-%m-%d').date(), now_nep.time())  
        self.delivery_datetime = delivery_datetime
        self.state= 'delivered'
        if delivery_id:
            delivery_id.state = 'delivered'
            delivery_id.delivery_time = now_nep.strftime("%H:%M:%S")
            delivery_id.update_time = now_nep.strftime("%H:%M:%S")
            print("delivery_time", delivery_id.delivery_time)
            delivery_id.scheduled_date_to = fields.Date.today()
            print("scheduled_date_to", delivery_id.scheduled_date_to)
            delivery_id.request_id.delivery_date = fields.Date.today()
            print("delivery_date", delivery_id.request_id.delivery_date)

            # Send SMS
            message = f"Dear {delivery_id.customer_name.name}, your order {delivery_id.name} has been successfully delivered on {fields.Date.today()}. Thank you for choosing us!"
            self._send_sms_notification(delivery_id.customer_name.phone, message)
                
            # Send email
            self._send_delivery_confirmation_email(delivery_id)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Delivery Order Proof',
            'res_model': 'transport.pod',  # Replace with the target model
            'view_mode': 'form',
            'context':{
                'default_order_id':delivery_id.id,
                'default_pod_date':fields.Date.today(),
            },
            'res_id': False,  # Open the specific record if found
            'target': 'new', 
        }
        # kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        # # print("timezone", kathmandu_tz)
        # now_nep = datetime.now(kathmandu_tz)
        # # print("now_nep", now_nep)
        # self.delivery_time = now_nep.strftime("%H:%M:%S")
        # # print("delivery_time", self.delivery_time)
        # # Set the scheduled_date_to to today's date
        # self.scheduled_date_to = fields.Date.today()
        # # print("scheduled_date_to", self.scheduled_date_to)
        # self.state = 'delivered'
        # return self._reload_action()
    @api.depends('from_date','to_date')
    def _compute_bs_date(self):
        for record in self:
            if record.to_date:
                to_nepali_date = nepali_datetime.date.from_datetime_date(record.to_date)
                record.to_date_bs = to_nepali_date.strftime('%Y-%m-%d')
            else:
                record.to_date_bs = False
            if record.from_date:
                from_nepali_date = nepali_datetime.date.from_datetime_date(record.from_date)
                record.from_date_bs = from_nepali_date.strftime('%Y-%m-%d')
            else:
                record.from_date_bs = False
            if record.pickup_date:
                pickup_nepali_date = nepali_datetime.date.from_datetime_date(record.pickup_date)
                record.pickup_date_bs = pickup_nepali_date.strftime('%Y-%m-%d')
            else:
                record.pickup_date_bs = False
            if record.delivery_date:
                delivery_nepali_date = nepali_datetime.date.from_datetime_date(record.delivery_date)
                record.delivery_date_bs = delivery_nepali_date.strftime('%Y-%m-%d')
            else:
                record.delivery_date_bs = False
    @api.depends('shift_start', 'shift_end','from_date','to_date')
    def _compute_work_hours(self):
        for record in self:
            if record.from_date and record.to_date:
                from_date = fields.Date.from_string(record.from_date) if isinstance(record.from_date, str) else record.from_date
                to_date = fields.Date.from_string(record.to_date) if isinstance(record.to_date, str) else record.to_date
                
                if to_date < from_date:
                    record.total_working_period = "Invalid date range"
                    continue
                
                delta = (to_date - from_date).days + 1  # Inclusive count
                working_days = delta
                record.total_days = working_days
                
                if record.shift_start and record.shift_end:  
                    try:
                        def float_to_str(time_value):
                            if isinstance(time_value, float):
                                hours = int(time_value)  
                                minutes = int((time_value - hours) * 60)  
                                time_str = f"{hours:02}:{minutes:02}"
                                return time_str
                            return time_value


                        def float_to_time(time_value):
                            if isinstance(time_value, float):
                                hours = int(time_value)  
                                minutes = int((time_value - hours) * 60)  
                                time_str = f"{hours:02}:{minutes:02}"
                                time_obj = datetime.strptime(time_str, "%H:%M").time()
                                return time_obj
                            return time_value
                        
                        try:
                            start_time = float(record.shift_start) if isinstance(record.shift_start, (str, float)) else 0.0
                            end_time = float(record.shift_end) if isinstance(record.shift_end, (str, float)) else 0.0
                            
                
                        except ValueError:
                            print("Invalid time format for shift_start or shift_end.")
                            return

                        shift_start_time = float_to_time(start_time)
                        shift_end_time = float_to_time(end_time)
            
                    
                        today = datetime.today().date()
                        shift_start_datetime = datetime.combine(today, shift_start_time)
                        shift_end_datetime = datetime.combine(today, shift_end_time)

                        self.start_time_shift = float_to_str(shift_start_time)
                        self.end_time_shift = float_to_str(shift_end_time)

                        # If shift end is earlier than shift start, it means the shift passed midnight
                        if shift_end_datetime < shift_start_datetime:
                            shift_end_datetime += timedelta(days=1)  # Add one day to end time

                        duration = shift_end_datetime - shift_start_datetime

                        total_hours = duration.total_seconds() // 3600  
                        total_minutes = (duration.total_seconds() % 3600) // 60
                        
            
                        total_work_time = f"{int(total_hours)} hr {int(total_minutes)} minutes"
                        # total_work_time = total_hours + (total_minutes / 60)
                        # print('Total work hours:', total_work_time)
                        # print('Total work hours:', type(total_work_time))
                        self.total_work_hours = total_work_time

                    except ValueError:
                        print("Invalid time format for shift_start or shift_end.")
                else:
                    print("shift_start or shift_end is not provided or invalid.")


    @api.model
    def create(self, vals):
        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%gdfgdfgfdg")
        return super().create(vals)

    def send_notification(self, order_name=None):
        kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        now_nep = datetime.now(kathmandu_tz)
        now_nep = now_nep.replace(microsecond=0)
        if now_nep.tzinfo is not None:
            now_nep = now_nep.replace(tzinfo=None)
        date = now_nep.date()
        order_id = self.env['transport.order'].search([('name', '=', order_name)], limit=1)
        customer_name    = order_id.customer_name.name if order_id else 'N/A'
        driver_name      = order_id.assignment_ids.driver_id.name if order_id.assignment_ids.driver_id else 'N/A'
        vehicle_number   = order_id.assignment_ids.vehicle_id.final_number if order_id.assignment_ids.vehicle_id else 'N/A'
        delivery_address = order_id.delivery_location or 'N/A'
        pickup_location  = order_id.pickup_location or 'N/A'
        order_name       = order_id.name if order_id else 'N/A'
        # customer_email   = order_id.customer_name.email if self.order_id.customer_name and self.order_id.customer_name.email else False
        
        notify_transport(
            env=self.env,
            notification_type='process',
            customer_name     = customer_name,
            driver_name       = driver_name,
            order_name        = order_name,
            vehicle_number    = vehicle_number,
            pickup_location   = pickup_location,
            delivery_location = delivery_address,
            order_id          = order_id,
            date              = date
        )
class DriverPerformance(models.Model):
    _name = 'driver.performance'
    _description = 'Driver Performance Monitoring'

    driver_id = fields.Many2one('driver.details', string='Driver', required=True)
    speed = fields.Float(string='Average Speed (km/h)')
    route_deviation = fields.Boolean(string='Route Deviation')
    idle_time = fields.Float(string='Idle Time (hours)')
    accident_reports = fields.Text(string='Accident Reports')
    passenger_feedback = fields.Text(string='Passenger Feedback')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    safety_violations = fields.One2many('custom.fine.penalty','driver_performance', string='Safety Violations')
    safety_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor')
    ], string='Safety Rating')
    date = fields.Date(string='Date')
    date_bs = fields.Char(string='Date (BS)', compute='_compute_bs_date')


    route = fields.Many2one('fleet.route',string='Route Name')
    checkpoints = fields.Many2one('fleet.route.checkpoint',string='Checkpoints')
    
   
    @api.depends('date')
    def _compute_bs_date(self):
        for record in self:
            if record.date:
                arrival_nepali_date = nepali_datetime.date.from_datetime_date(record.date)
                record.date_bs = arrival_nepali_date.strftime('%Y-%m-%d')
            else:
                record.date_bs = False

    @api.model
    def create(self, values):
        # Automatically set the driver_id to the current driver
        driver_id = self._context.get('active_id')  # Get the current driver ID from context
        if driver_id:
            values['driver_id'] = driver_id
            
        new_record = super(DriverPerformance, self).create(values)
        violations = f"{new_record.safety_violations.details_id.fine_type.name}: {new_record.safety_violations.details_id.fine_reason}"
        
        # Create a record in driver.performance.history after creating the performance record
        self.env['driver.performance.dashboard'].create({
            'driver_id': new_record.driver_id.id,
            'route_name': new_record.route.name.name,
            'driver_name': new_record.driver_id.name,
            'violation_type': new_record.safety_violations.fine_name,
            'violation_details': violations,
            'date': new_record.date_bs,
            'date_bs': new_record.date_bs,
            'safety_rating': new_record.safety_rating,
            'speed': new_record.speed,
            'accident_reports': new_record.accident_reports,
            # 'violation_count': new_record.violation_
        })
        print("successfully created")
        return new_record
    @api.model
    def write(self, values):
        for record in self:
            super(DriverPerformance, record).write(values)
            
            violations = f"{record.safety_violations.details_id.fine_type.name}: {record.safety_violations.details_id.fine_reason}"
        
            existing_dashboard_record = self.env['driver.performance.dashboard'].search([
                ('driver_id', '=', record.driver_id.id)
            ], limit=1)
            if existing_dashboard_record:
                existing_dashboard_record.route_name = record.route.name.name
                existing_dashboard_record.driver_name = record.driver_id.name
                existing_dashboard_record.violation_type = record.safety_violations.fine_name
                existing_dashboard_record.violation_details = violations
                existing_dashboard_record.date = record.date_bs
                existing_dashboard_record.safety_rating = record.safety_rating
                existing_dashboard_record.speed = record.speed
                existing_dashboard_record.accident_reports = record.accident_reports

        return True

   
        
class DriverPerformanceDashboard(models.Model):
    _name = 'driver.performance.dashboard'
    _description = 'Driver Performance Dashboard'

    driver_id = fields.Many2one('driver.details', string='Driver', required=True)
    route_name = fields.Char(string='Route Name', required=True)
    driver_name = fields.Char(string='Driver Name', required=True)
    violation_type = fields.Char(string='Violation Type', required=True)
    violation_details = fields.Text(string='Violation Details')
    date = fields.Char(string='Date', required=True)
    safety_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor')
    ], string='Safety Rating')
    speed = fields.Float(string='Speed')
    accident_reports = fields.Text(string='Accident Reports')
    date_bs = fields.Char(string='Date (BS)')
    # You can optionally include violation_count if needed
    # violation_count = fields.Integer(string='Violation Count', default=1)
    
   

    
    
        
class ViolationsType(models.Model):
    _name = 'violations.type'
    _description = 'Safety Violations'

    name = fields.Char(string='Violation Type', required=True)
    code = fields.Char(string='Violation Code')

class DriverTraining(models.Model):
    _name = 'driver.training'
    _description = 'Training & Certification Management'

    driver_id = fields.Many2one('driver.details', string='Driver')
    training_completed = fields.Boolean(string='Training Completed')
    training_type = fields.Selection([
        ('safety', 'Safety Training'),
        ('defensive', 'Defensive Driving'),
        ('certification', 'Certification Renewal')
    ], string='Training Type')
    cert_issue_date = fields.Date(string='Issued Date')
    cert_issue_date_bs = fields.Char(string='Issued Date',compute='_compute_bs_date', store=True)

    cert_expiry_date = fields.Date(string='Expiry Date')
    cert_expiry_date_bs = fields.Char(string='Expiry Date(BS)',compute='_compute_bs_date', store=True)

    next_training_date = fields.Date(string='Next Training Due')
    next_training_date_bs = fields.Char(string='Next Training Due(BS)',compute='_compute_bs_date', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    

    training_document_ids = fields.One2many("training.document", "document_id")
    
    @api.depends('cert_issue_date', 'cert_expiry_date', 'next_training_date')
    def _compute_bs_date(self):
        for record in self:
            if record.cert_issue_date:
                cert_issue_date_nepali = nepali_datetime.date.from_datetime_date(record.cert_issue_date)
                record.cert_issue_date_bs = cert_issue_date_nepali.strftime('%Y-%m-%d')
            else:
                record.cert_issue_date_bs = False

            if record.cert_expiry_date:
                cert_expiry_date_nepali = nepali_datetime.date.from_datetime_date(record.cert_expiry_date)
                record.cert_expiry_date_bs = cert_expiry_date_nepali.strftime('%Y-%m-%d')
            else:
                record.cert_issue_date_bs = False

            if record.next_training_date:
                next_training_date_nepali = nepali_datetime.date.from_datetime_date(record.next_training_date)
                record.next_training_date_bs = next_training_date_nepali.strftime('%Y-%m-%d')
            else:
                record.next_training_date_bs = False

# class VehicleDetails(models.Model):
#     _name = 'vehicle.details'
#     _description = 'Vehicle Information'

#     name = fields.Char(string='Vehicle ID', required=True)
#     driver_ids = fields.One2many('duty.allocation', 'vehicle_id', string='Assigned Drivers')

class HelperDetails(models.Model):
    _name = 'helper.details'
    _description = 'Helper Information'

    name = fields.Char(string='Helper Name', required=True)
    name_np = fields.Char(string= 'Helper Name(np)')
    address = fields.Text(string='Address')
    phone_number = fields.Char(string='Phone Number', size=10)
    citizenship_number = fields.Char(string='Citizenship Number')
    available = fields.Boolean(string="Is Available ?", default=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Related Employee',
        readonly=True,
        ondelete='set null',
    )
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    HELPER_EMPLOYEE_FIELD_MAP = {
        'name': 'name',
        'phone_number': 'mobile_phone',
        'gender': 'gender',
        'job_title': 'job_title',
    }
    job_title = fields.Char(string='Job Title', default='Helper')

    # Phone number should be 10 digits and start with 97 or 98
    @api.depends('phone_number')
    def  _check_phone_format(self):
        for record in self:
            if record.phone_number and len(record.phone_number) != 10:
                raise ValidationError("Phone number should be 10 digits.")
            elif record.phone_number and not record.phone_number.startswith("97") and not record.phone_number.startswith("98"):
                raise ValidationError("Phone number should start with 97 or 98.")

    @api.model
    def create(self, vals):
        # Create helper record
        helper = super().create(vals)
        
        # Build employee vals - without address
        emp_vals = {
            'name': helper.name,
            'job_title': 'Helper',
            'gender': helper.gender,
            'mobile_phone': helper.phone_number,
        }
        print("emp_vals", emp_vals)
        
        # Create employee
        employee = self.env['hr.employee'].create(emp_vals)
        print("employee", employee)
        helper.employee_id = employee.id
        print("helper.employee_id", helper.employee_id)
        
        return helper

    def write(self, vals):
        # Update helper record
        res = super().write(vals)

        for helper in self.filtered('employee_id'):
            emp_vals = {}
            
            # Update basic employee fields
            if 'name' in vals:
                emp_vals['name'] = vals['name']
            if 'gender' in vals:
                emp_vals['gender'] = vals['gender']
            if 'phone_number' in vals:
                emp_vals['mobile_phone'] = vals['phone_number']
            
            # Write employee updates
            if emp_vals:
                helper.employee_id.write(emp_vals)
        
        return res