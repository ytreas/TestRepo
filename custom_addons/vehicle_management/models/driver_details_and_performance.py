from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import time, datetime, timedelta
from pytz import timezone
import nepali_datetime
from ..utils.dashboard_notification import Utilities 

class DriverDetails(models.Model):
    _name = 'driver.details'
    _description = 'Driver Details Management'

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

    @api.depends('license_expiry_date')
    def _compute_bs_date(self):
        for record in self:
            if record.license_expiry_date:
                arrival_nepali_date = nepali_datetime.date.from_datetime_date(record.license_expiry_date)
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
        
                    
class DutyAllocation(models.Model):
    _name = 'duty.allocation'
    _description = 'Duty Allocation Management'

    duty_name = fields.Char(string='Duty Name', required=True)
    driver_id = fields.Many2one('driver.details', string='Driver')
    vehicle_id = fields.Many2one('vehicle.number', string='Assigned Vehicle', required=True, ondelete='cascade')
    shift_start = fields.Char(string='Shift Start Time')
    shift_end = fields.Char(string='Shift End Time') 
    start_time_shift = fields.Char(string='Shift Start Time')
    end_time_shift = fields.Char(string='Shift End Time') 
    total_work_hours = fields.Char(string='Total Work Hours', compute='_compute_work_hours',store=True)
    rest_breaks = fields.Float(string='Rest Breaks Taken (hours)')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('shift_start', 'shift_end')
    def _compute_work_hours(self):
        if self.shift_start and self.shift_end:  
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
                    start_time = float(self.shift_start) if isinstance(self.shift_start, (str, float)) else 0.0
                    end_time = float(self.shift_end) if isinstance(self.shift_end, (str, float)) else 0.0
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