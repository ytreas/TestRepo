from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import nepali_datetime
from datetime import datetime, timedelta
from ..models.maintenance_management import convert_to_bs_date
from nepali_datetime import date as nepali_date

def parse_nepali_date(nepali_date_str):
    year, month, day = map(int, nepali_date_str.split('-'))
    return (year, month, day)

def gregorian_to_nepali(gregorian_date):
    return (gregorian_date.year, gregorian_date.month, gregorian_date.day)   

# Base Service Model
class BaseServiceModel(models.AbstractModel):
    _name = 'base.service.model'
    _description = 'Base Service Model'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    create_date = fields.Datetime(readonly=True)
    write_date = fields.Datetime(readonly=True)
    notes = fields.Text(string='Notes')

# Service Category Model
class ServiceCategory(models.Model):
    _name = 'service.category'
    _description = 'Service Category'
    _inherit = ['base.service.model']

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Category Code', required=True)
    service_type_ids = fields.One2many('service.type', 'category_id', string='Service Types')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    _sql_constraints = [
        ('unique_category_code', 'unique(code)', 'Category code must be unique!')
    ]

# Service Type Model
class ServiceType(models.Model):
    _name = 'service.type'
    _description = 'Service Type'
    _inherit = ['base.service.model']

    name = fields.Char(string='Service Type', required=True)
    category_id = fields.Many2one('service.category', string='Category', ondelete='cascade', required=True)
    standard_cost = fields.Float(string='Standard Cost')
    description = fields.Text(string='Description')
    average_duration = fields.Float(string='Average Duration (Hours)')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_category_unique', 'unique(name, category_id)', 'Service type must be unique per category!')
    ]

# Notification Mode Model
class NotificationMode(models.Model):
    _name = 'notification.mode'
    _description = 'Notification Mode'
    _inherit = ['base.service.model']

    name = fields.Char(string='Notification Mode', required=True)
    is_email = fields.Boolean(string='Email Notification')
    is_sms = fields.Boolean(string='SMS Notification')
    template_id = fields.Many2one('mail.template', string='Email Template')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

# Services Performed Model
class ServicesPerformed(models.Model):
    _name = 'services.performed'
    _description = 'Services Performed'
    _inherit = ['base.service.model']

    name = fields.Many2one('service.type', string='Service Type', ondelete='cascade', required=True)
    standard_cost = fields.Float(related='name.standard_cost', string='Standard Cost')
    actual_cost = fields.Float(string='Actual Cost')
    variance = fields.Float(compute='_compute_variance', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('standard_cost', 'actual_cost')
    def _compute_variance(self):
        for record in self:
            record.variance = record.actual_cost - record.standard_cost

# Service Execution Line Model
class ServiceExecutionLine(models.Model):
    _name = 'service.execution.line'
    _description = 'Services Execution Line'
    _inherit = ['base.service.model']

    name = fields.Many2one('services.performed', string='Services', ondelete='cascade', required=True)
    cost_per_service = fields.Float(string='Service Cost', required=True)
    service_execution_id = fields.Many2one('service.execution', ondelete='cascade', string='Service Execution')
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(compute='_compute_duration', store=True)
    technician_notes = fields.Text(string='Technician Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                duration = (record.end_time - record.start_time).total_seconds() / 3600
                record.duration = round(duration, 2)
            else:
                record.duration = 0.0

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for record in self:
            if record.start_time and record.end_time and record.start_time > record.end_time:
                raise ValidationError("End time cannot be before start time")

# Manager class to encapsulate scheduling-related business logic.
class ServiceSchedulingManager:
    def __init__(self, scheduling):
        self.scheduling = scheduling

    # Method to schedule the next service for the vehicle.
    def schedule(self): 
        sch = self.scheduling
        # Generate schedule code if not already set.
        if sch.code == 'New':
            schedule_count = sch.search_count([])
            sch.code = f"SCH-{schedule_count + 1:03d}"
        schedule_number = sch.code.split('-')[1]
        execution_code = f"EXE/{schedule_number}"

        # Create the service execution record.
        execution_vals = {
            'code': execution_code,
            'vehicle_id': sch.vehicle_id.id,
            'service_scheduling_id': sch.id,
            'start_time': sch.next_service_due_date,
            'service_location': sch.vehicle_id.company_id.name,
            'state': 'draft'
        }
        execution = sch.env['service.execution'].create(execution_vals)

        # Create execution lines based on the selected service types.
        for service_type in sch.service_type_id:
            performed_service = sch.env['services.performed'].search([
                ('name', '=', service_type.id)
            ], limit=1)
            if not performed_service:
                performed_service = sch.env['services.performed'].create({
                    'name': service_type.id,
                    'standard_cost': service_type.standard_cost,
                    'actual_cost': service_type.standard_cost,
                })

            line_vals = {
                'name': performed_service.id,
                'cost_per_service': service_type.standard_cost,
                'service_execution_id': execution.id,
                'start_time': sch.next_service_due_date,
            }
            sch.env['service.execution.line'].create(line_vals)

        sch.state = 'scheduled'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action': 'reload_page'},
        }

    # Method to send a reminder email to the vehicle owner.
    def send_reminder(self):
        sch = self.scheduling
        if sch.notification_mode_id.template_id:
            sch.notification_mode_id.template_id.send_mail(sch.id, force_send=True)
        sch.reminder_sent = True


# Service Scheduling Model
class ServiceScheduling(models.Model):
    _name = 'service.scheduling'
    _description = 'Service Scheduling & Alerts'
    _inherit = ['base.service.model', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'code'
    _order = 'create_date desc'

    code = fields.Char(string="Schedule Code", readonly=True, default='New')
    vehicle_id = fields.Many2one('vehicle.number', string='Vehicle', required=True, ondelete='cascade', tracking=True)
    last_service_date = fields.Date(string='Last Service Date', required=True)
    last_service_date_bs = fields.Char(string='Last Service Date (BS)', store=True, compute='_compute_service_dates_bs')
    next_service_due_date = fields.Date(string='Next Service Due Date', required=True, tracking=True)
    next_service_due_date_bs = fields.Char(string='Next Service Due Date (BS)', store=True, compute='_compute_service_dates_bs')
    service_type_id = fields.Many2many('service.type', string='Service Type', required=True)
    notification_mode_id = fields.Many2one('notification.mode', string='Notification Mode', required=True)
    execution_ids = fields.One2many('service.execution', 'service_scheduling_id', string="Service Executions")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High')
    ], default='1', tracking=True)
    reminder_sent = fields.Boolean(default=False)
    color = fields.Integer(string='Color Index')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    is_today = fields.Boolean(string='Is Today', compute='_compute_date_filters', store=True)
    is_this_week = fields.Boolean(string='Is This Week', compute='_compute_date_filters', store=True)
    is_this_month = fields.Boolean(string='Is This Month', compute='_compute_date_filters', store=True)
    create_date = fields.Datetime(readonly=True)
    create_date_only = fields.Date(string="Create Date Only", compute='_compute_create_date_only', store=True)
    execution_count = fields.Integer(
        string='Execution Count', 
        compute='_compute_execution_count', 
        store=True
    )

    @api.depends('execution_ids')
    def _compute_execution_count(self):
        for record in self:
            record.execution_count = len(record.execution_ids)

    @api.constrains('execution_ids')
    def _check_single_execution(self):
        for record in self:
            if record.execution_count > 1:
                raise ValidationError(_(
                    "Only one service execution is allowed per schedule. "
                    "Schedule: %s already has an execution." % record.code
                ))

    def _compute_create_date_only(self):
        for record in self:
            if record.create_date:
                record.create_date_only = record.create_date.date()
            else:
                record.create_date_only = False
                
    # Method to compute date filters
    @api.depends('next_service_due_date')
    def _compute_date_filters(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_today = record.next_service_due_date == today
            if record.next_service_due_date:
                dt_date = fields.Date.from_string(record.next_service_due_date)
                dt_today = fields.Date.from_string(today)
                start_of_week = dt_today - timedelta(days=(dt_today.weekday() + 1) % 7)
                end_of_week = start_of_week + timedelta(days=6)
                record.is_this_week = start_of_week <= dt_date <= end_of_week

                today_nepali_date = nepali_datetime.date.from_datetime_date(dt_today)
                date_bs_nepali = parse_nepali_date(record.next_service_due_date_bs)
                start_of_month = today_nepali_date.replace(day=1)
                start_of_month_nepali = gregorian_to_nepali(start_of_month)
                record.is_this_month = date_bs_nepali >= start_of_month_nepali
            else:
                record.is_today = False
                record.is_this_week = False
                record.is_this_month = False        

    # Method to force recomputation of date filters
    def recompute_date_filters(self):
        """Force recomputation of date filters on all records."""
        records = self.search([])
        for rec in records:
            rec.write({'next_service_due_date': rec.next_service_due_date}) 

    # Method to compute service dates
    @api.depends('last_service_date', 'next_service_due_date')
    def _compute_service_dates_bs(self):
        for record in self:
            record.last_service_date_bs = convert_to_bs_date(record.last_service_date)
            record.next_service_due_date_bs = convert_to_bs_date(record.next_service_due_date)

    # Method to validate service dates
    # @api.constrains('last_service_date', 'next_service_due_date')
    # def _check_service_dates(self):
    #     for record in self:
    #         if record.last_service_date and record.next_service_due_date:
    #             if record.next_service_due_date <= record.last_service_date:
    #                 raise ValidationError("Next Service Due Date must be after the Last Service Date.")

    # Method to schedule service

    def action_schedule(self):
        self.ensure_one()
        # Check if execution already exists
        if self.execution_ids:
            raise ValidationError(_(
                "Cannot create new execution. Schedule %s already has "
                "an execution record." % self.code
            ))
        manager = ServiceSchedulingManager(self)
        return manager.schedule()
    
    # Method to cancel service
    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancelled'

    # Method to send reminder
    def action_send_reminder(self):
        self.ensure_one()
        manager = ServiceSchedulingManager(self)
        manager.send_reminder()

    # Method to create service scheduling
    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('service.scheduling') or 'New'
        return super(ServiceScheduling, self).create(vals)

# Model for Parts Replaced
class PartsReplaced(models.Model):
    _name = 'parts.replaced'
    _description = 'Parts Replaced'
    _inherit = ['base.service.model']

    name = fields.Char(string='Part Name', required=True)
    part_number = fields.Char(string='Part Number')
    cost = fields.Float(string='Cost', required=True)
    warranty_period = fields.Integer(string='Warranty Period (Days)')
    warranty_end_date = fields.Date(compute='_compute_warranty_end_date', store=True)
    service_execution_id = fields.Many2one('service.execution', string='Service Execution', ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    # Method to compute warranty end date
    @api.depends('service_execution_id.end_time', 'warranty_period')
    def _compute_warranty_end_date(self):
        for record in self:
            if record.service_execution_id.end_time and record.warranty_period:
                record.warranty_end_date = record.service_execution_id.end_time + timedelta(days=record.warranty_period)
            else:
                record.warranty_end_date = False

# Model for Service Execution State Manager
class ServiceExecutionStateManager:
    def __init__(self, execution):
        self.execution = execution

    # Method to start service
    def start_service(self):
        exe = self.execution
        exe.state = 'in_progress'
        if exe.service_scheduling_id:
            exe.service_scheduling_id.state = 'in_progress'

    # Method to complete service
    def complete_service(self):
        exe = self.execution
        exe.state = 'completed'
        if exe.service_scheduling_id:
            exe.service_scheduling_id.state = 'done'
        self._create_or_update_history()

    # Method to cancel service
    def cancel_service(self):
        exe = self.execution
        exe.state = 'cancelled'
        if exe.service_scheduling_id:
            exe.service_scheduling_id.state = 'cancelled'

    # Method to create or update history
    def _create_or_update_history(self):
        exe = self.execution
        history_vals = {
            'vehicle_id': exe.vehicle_id.id,
            'service_date': exe.end_time or fields.Date.today(),
            'service_record': exe.service_record,
            'cost_trend': exe.cost_incurred,
            'odometer_reading': exe.odometer_reading,
        }
        if exe.history_id:
            exe.history_id.write(history_vals)
        else:
            history = exe.env['service.history'].create(history_vals)
            exe.history_id = history.id

# Model for Service Execution
class ServiceExecution(models.Model):
    _name = 'service.execution'
    _description = 'Service Execution & Tracking'
    _inherit = ['base.service.model', 'mail.thread']
    _rec_name = 'code'
    _order = 'create_date desc'

    code = fields.Char(string="Execution Code", readonly=True, default='New')
    vehicle_id = fields.Many2one('vehicle.number', string='Vehicle', required=True, ondelete='cascade', tracking=True)
    service_provider = fields.Char(string='Service Provider', tracking=True)
    start_time = fields.Date(string='Start Date', required=True, tracking=True)
    end_time = fields.Date(string='End Date', tracking=True)
    parts_replaced_ids = fields.One2many('parts.replaced', 'service_execution_id', string='Parts Replaced')
    cost_incurred = fields.Float(string='Cost Incurred (NPR)', compute='_compute_total_cost_incurred', store=True)
    service_quality_feedback = fields.Text(string='Service Quality Feedback')
    execution_line_id = fields.One2many('service.execution.line', 'service_execution_id', string='Service Execution')
    service_location = fields.Text(string="Service Location")
    service_date_bs = fields.Char(string='Service Date(BS)', compute='_compute_nepali_dates', store=True)
    start_time_bs = fields.Char(string='Start Service Date(BS)', compute='_compute_nepali_dates', store=True)
    service_scheduling_id = fields.Many2one('service.scheduling', ondelete='cascade', string="Service Scheduling Code")
    service_record = fields.Text(string="Service Record", compute='_compute_service_record', store=True)
    history_id = fields.Many2one('service.history', ondelete='cascade', string='Service History')
    odometer_reading = fields.Float(string='Odometer Reading (Km)')
    last_odometer_reading = fields.Float(string='Last Odometer Reading (Km)')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)
    date_bs = fields.Char(string='Service Date(BS)', compute='_compute_nepali_dates', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    next_service_date = fields.Date(string='Next Service Date', tracking=True, store=True)
    next_service_date_bs = fields.Char(string='Next Service Date(BS)', compute='_compute_nepali_dates', store=True)
    invoice_no = fields.Char(string='Invoice No.', tracking=True)
    
    @api.constrains('start_time', 'end_time', 'next_service_date')
    def _check_next_service_date(self):
        for record in self:
            if record.next_service_date:
                if record.end_time and record.next_service_date <= record.end_time:
                    raise ValidationError(_("Next Service Date must be after End Date."))
                if record.start_time and record.next_service_date <= record.start_time:
                    raise ValidationError(_("Next Service Date must be after Start Date."))
                    
    # Method to compute total cost incurred
    @api.depends('execution_line_id.cost_per_service', 'parts_replaced_ids.cost')
    def _compute_total_cost_incurred(self):
        for record in self:
            execution_cost = sum(line.cost_per_service for line in record.execution_line_id)
            parts_cost = sum(part.cost for part in record.parts_replaced_ids)
            record.cost_incurred = execution_cost + parts_cost

    # Method to compute service record
    @api.depends('vehicle_id', 'service_provider', 'parts_replaced_ids', 'service_location', 'cost_incurred')
    def _compute_service_record(self):
        for record in self:
            parts_replaced = ", ".join(record.parts_replaced_ids.mapped('name')) if record.parts_replaced_ids else 'None'
            record.service_record = (
                f"Vehicle: {record.vehicle_id.final_number or ''}\n"
                f"Service Provider: {record.service_provider or ''}\n"
                f"Location: {record.service_location or ''}\n"
                f"Parts Replaced: {parts_replaced}\n"
                f"Total Cost: {record.cost_incurred or 0.0} NPR"
            )

    # Method to compute nepali dates
    @api.depends('start_time', 'end_time', 'next_service_date')
    def _compute_nepali_dates(self):
        for record in self:
            record.start_time_bs = convert_to_bs_date(record.start_time)
            record.service_date_bs = convert_to_bs_date(record.end_time)
            record.date_bs = convert_to_bs_date(record.end_time)
            record.next_service_date_bs = convert_to_bs_date(record.next_service_date)

    # Method to check dates
    @api.constrains('start_time', 'end_time')
    def _check_dates(self):
        for record in self:
            if record.end_time and record.start_time > record.end_time:
                raise ValidationError("End date cannot be before start date")

    # Method to check odometer
    @api.constrains('odometer_reading', 'last_odometer_reading')
    def _check_odometer(self):
        for record in self:
            if record.odometer_reading and record.last_odometer_reading:
                if record.odometer_reading < record.last_odometer_reading:
                    raise ValidationError("Current odometer reading cannot be less than last reading")

    # Method to start service
    def action_start_service(self):
        self.ensure_one()
        manager = ServiceExecutionStateManager(self)
        manager.start_service()

    # Method to complete service
    def action_complete_service(self):
        self.ensure_one()
        manager = ServiceExecutionStateManager(self)
        manager.complete_service()

    # Method to cancel service
    def action_cancel_service(self):
        self.ensure_one()
        manager = ServiceExecutionStateManager(self)
        manager.cancel_service()

    # Override create method
    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            execution_count = self.search_count([]) + 1
            vals['code'] = f"EXE/{execution_count:03d}"
        if 'vehicle_id' in vals:
            vehicle = self.env['vehicle.number'].browse(vals['vehicle_id'])
            vals['last_odometer_reading'] = vehicle.latest_odometer
        return super(ServiceExecution, self).create(vals)

# Model for service history
class ServiceHistory(models.Model):
    _name = 'service.history'
    _description = 'Service History & Analysis'
    _inherit = ['base.service.model']
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    vehicle_id = fields.Many2one('vehicle.number', string='Vehicle', required=True, ondelete='cascade')
    service_date = fields.Date(required=True)
    service_date_bs = fields.Char(compute='_compute_nepali_date', store=True)
    service_record = fields.Text(string='Service Record', required=True)
    cost_trend = fields.Float(string='Cost Trend (NPR)')
    performance_after_servicing = fields.Text(string='Performance After Servicing')
    odometer_reading = fields.Float(string='Odometer Reading at Service')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    is_today = fields.Boolean(string='Is Today', compute='_compute_date_filters', store=True)
    is_this_week = fields.Boolean(string='Is This Week', compute='_compute_date_filters', store=True)
    is_this_month = fields.Boolean(string='Is This Month', compute='_compute_date_filters', store=True)

    # Method to compute date filters
    @api.depends('service_date')
    def _compute_date_filters(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_today = record.service_date == today

            if record.service_date:
                dt_date = fields.Date.from_string(record.service_date)
                dt_today = fields.Date.from_string(today)

                start_of_week = dt_today - timedelta(days=(dt_today.weekday() + 1) % 7)
                end_of_week = start_of_week + timedelta(days=6)
                record.is_this_week = start_of_week <= dt_date <= end_of_week
                
                # Convert today's Gregorian date to Nepali date
                today_nepali_date = nepali_datetime.date.from_datetime_date(today)
                
                # Parse the service_date_bs, which returns a tuple, then convert to nepali_date
                date_bs_nepali_tuple = parse_nepali_date(record.service_date_bs)
                date_bs_nepali = nepali_date(
                    date_bs_nepali_tuple[0],
                    date_bs_nepali_tuple[1],
                    date_bs_nepali_tuple[2]
                )
                
                # Compute the start of the month in Nepali date
                start_of_month = today_nepali_date.replace(day=1)
                start_of_month_nepali_tuple = gregorian_to_nepali(start_of_month)
                start_of_month_nepali = nepali_date(
                    start_of_month_nepali_tuple[0],
                    start_of_month_nepali_tuple[1],
                    start_of_month_nepali_tuple[2]
                )
                
                record.is_this_month = date_bs_nepali >= start_of_month_nepali
            else:
                record.is_today = False
                record.is_this_week = False
                record.is_this_month = False  

    # Method to force recomputation of date filters
    def recompute_date_filters(self):
        """Method to force recomputation of date filters on all records."""
        records = self.search([])
        for rec in records:
            rec.write({'service_date': rec.service_date})

    # Method to generate vehicle number and service date
    @api.depends('vehicle_id', 'service_date')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.vehicle_id.final_number or ''} - {record.service_date or ''}"

    # Method to compute nepali date
    @api.depends('service_date')
    def _compute_nepali_date(self):
        for record in self:
            record.service_date_bs = convert_to_bs_date(record.service_date)