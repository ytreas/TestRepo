from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import nepali_datetime
from datetime import datetime, timedelta

# Utility: Parse a Nepali date string into a tuple of (year, month, day).
def parse_nepali_date(nepali_date_str):
    year, month, day = map(int, nepali_date_str.split('-'))
    return (year, month, day)

# Utility: Convert a Gregorian date to a tuple of (year, month, day).
def gregorian_to_nepali(gregorian_date):
    return (gregorian_date.year, gregorian_date.month, gregorian_date.day)   

# Utility: Convert a Gregorian date to a Nepali BS date string.
def convert_to_bs_date(date_val):
    if date_val:
        nep_date = nepali_datetime.date.from_datetime_date(date_val)
        return nep_date.strftime('%Y-%m-%d')
    return False

# Base Maintenance Model
class BaseMaintenance(models.AbstractModel):
    _name = 'base.maintenance'
    _description = 'Base Maintenance Model'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)
    create_date = fields.Datetime(readonly=True)
    write_date = fields.Datetime(readonly=True)

# Maintenance Request State Manager
class MaintenanceRequestStateManager:
    def __init__(self, request):
        self.request = request

    # Method to submit a maintenance request
    def submit(self):
        req = self.request
        req.state = 'submitted'
        # Automatically create a work order if none exists.
        if not req.work_order_ids:
            work_order_vals = {
                'maintenance_request_id': req.id,
                'scheduled_maintenance_date': req.scheduled_start,
                'estimated_cost': req.estimated_cost,
            }
            req.env['maintenance.work.order'].create(work_order_vals)
        if req.work_order_ids:
            req.work_order_ids.write({'state': 'submitted'})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action': 'reload_page'},
        }

    # Method to cancel a maintenance request
    def cancel(self):
        req = self.request
        req.state = 'cancelled'
        if req.work_order_ids:
            req.work_order_ids.write({'state': 'cancelled'})
        if req.execution_ids:
            req.execution_ids.write({'state': 'cancelled'})
        if req.completion_ids:
            req.completion_ids.write({'state': 'cancelled'})

# Maintenance Request Model
class MaintenanceRequest(models.Model):
    _name = 'maintenance.request'
    _inherit = ['base.maintenance']
    _description = 'Maintenance Request & Scheduling'
    _rec_name = 'code'
    _order = 'create_date desc'

    code = fields.Char(string='Request Code', required=True, copy=False, readonly=True, default='New')
    vehicle_id = fields.Many2one('vehicle.number', string='Vehicle', required=True, tracking=True)
    driver_id = fields.Many2one('driver.details', string='Driver', required=True, tracking=True)
    issue_description = fields.Text(string='Reported Issue Description', required=True, tracking=True)
    report_datetime = fields.Date(string='Report Date', required=True)
    report_date_bs = fields.Char(string='Report Date(BS)', compute='_compute_bs_date', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)
    estimated_cost = fields.Float(string='Estimated Cost')
    actual_cost = fields.Float(string='Actual Cost', compute='_compute_actual_cost', store=True)
    cost_variance = fields.Float(string='Cost Variance', compute='_compute_cost_variance', store=True)
    scheduled_start = fields.Date('Scheduled Start', default=fields.Date.context_today, tracking=True)
    scheduled_start_bs = fields.Char(string='Scheduled Start(BS)', compute='_compute_bs_date', store=True)
    scheduled_end = fields.Date('Scheduled End', default=fields.Date.context_today, tracking=True)
    scheduled_end_bs = fields.Char(string='Scheduled End(BS)', compute='_compute_bs_date', store=True)
    actual_start = fields.Date('Actual Start', tracking=True)
    actual_start_bs = fields.Char(string='Actual Start(BS)', compute='_compute_bs_date', store=True)
    actual_end = fields.Date('Actual End', tracking=True)
    actual_end_bs = fields.Char(string='Actual End(BS)', compute='_compute_bs_date', store=True)
    date_bs = fields.Char(string="Date Bs")  # for dashboard filters purposes
    priority_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Priority Level', required=True, tracking=True)
    estimated_downtime = fields.Float(string='Estimated Downtime (Hours)', help="Estimated downtime in hours")
    actual_downtime = fields.Float(string='Actual Downtime (Hours)', compute='_compute_actual_downtime', store=True)
    province = fields.Many2one('location.province', string='Province', required=True)
    district = fields.Many2one(
        'location.district', 
        string='District', 
        required=True, 
        domain="[('province_name', '=', province)]"
    )
    local_level = fields.Many2one(
        'location.palika', 
        string='Local Level', 
        required=True, 
        domain="[('district_name', '=', district)]"
    )
    ward_no = fields.Char(string='Ward No.', required=True)
    work_order_ids = fields.One2many('maintenance.work.order', 'maintenance_request_id', string='Work Orders')
    execution_ids = fields.One2many('maintenance.execution', 'maintenance_request_id', string='Executions')
    completion_ids = fields.One2many('maintenance.completion', 'maintenance_request_id', string='Completions')
    work_order_count = fields.Integer(string='Work Orders', compute='_compute_work_order_count')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    is_today = fields.Boolean(string='Is Today', compute='_compute_date_filters', store=True)
    is_this_week = fields.Boolean(string='Is This Week', compute='_compute_date_filters', store=True)
    is_this_month = fields.Boolean(string='Is This Month', compute='_compute_date_filters', store=True)
                
    # Method to compute date filters
    @api.depends('report_datetime')
    def _compute_date_filters(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_today = record.report_datetime == today
            if record.report_datetime:
                dt_date = fields.Date.from_string(record.report_datetime)
                dt_today = fields.Date.from_string(today)
                start_of_week = dt_today - timedelta(days=(dt_today.weekday() + 1) % 7)
                end_of_week = start_of_week + timedelta(days=6)
                record.is_this_week = start_of_week <= dt_date <= end_of_week

                today_nepali_date = nepali_datetime.date.from_datetime_date(dt_today)
                date_bs_nepali = parse_nepali_date(record.report_date_bs)
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
            rec.write({'report_datetime': rec.report_datetime})
    
    # Override the create method to generate a unique code
    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            count = self.search_count([]) + 1
            vals['code'] = f'REQ/{count:03d}'
        return super(MaintenanceRequest, self).create(vals)
    
    # Method to get the driver associated with the vehicle
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        self.driver_id = self.vehicle_id.driver_id if self.vehicle_id else False
     
    # Method to compute BS date
    @api.depends('report_datetime', 'scheduled_start', 'scheduled_end', 'actual_start', 'actual_end')
    def _compute_bs_date(self):
        for record in self:
            record.report_date_bs = convert_to_bs_date(record.report_datetime)
            record.scheduled_start_bs = convert_to_bs_date(record.scheduled_start)
            record.scheduled_end_bs = convert_to_bs_date(record.scheduled_end)
            record.actual_start_bs = convert_to_bs_date(record.actual_start)
            if record.actual_end:
                record.actual_end_bs = convert_to_bs_date(record.actual_end)
                record.date_bs = record.actual_end_bs
            else:
                record.actual_end_bs = False
                record.date_bs = False
    
    # Method to compute work order count
    @api.depends('work_order_ids')
    def _compute_work_order_count(self):
        for record in self:
            record.work_order_count = len(record.work_order_ids)
    
    # Method to view work orders
    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'name': _('Work Orders'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.work.order',
            'domain': [('maintenance_request_id', '=', self.id)],
            'context': {'default_maintenance_request_id': self.id},
        }
    
    # Method to compute actual downtime
    @api.depends('actual_start', 'actual_end')
    def _compute_actual_downtime(self):
        for record in self:
            if record.actual_start and record.actual_end:
                delta = record.actual_end - record.actual_start
                record.actual_downtime = delta.total_seconds() / 3600
            else:
                record.actual_downtime = 0.0
                
    # Method to handle province, district, and local level changes
    @api.onchange('province')
    def _onchange_province(self):
        self.district = False
        self.local_level = False

    # Method to handle district and local level changes
    @api.onchange('district')
    def _onchange_district(self):
        self.local_level = False

    # Method to compute actual cost
    @api.depends('completion_ids.total_cost')
    def _compute_actual_cost(self):
        for record in self:
            record.actual_cost = sum(record.completion_ids.mapped('total_cost'))

    # Method to compute cost variance
    @api.depends('estimated_cost', 'actual_cost')
    def _compute_cost_variance(self):
        for record in self:
            record.cost_variance = record.actual_cost - record.estimated_cost

    # Method to check schedule dates
    @api.constrains('scheduled_start', 'scheduled_end')
    def _check_schedule_dates(self):
        for record in self:
            if record.scheduled_end and record.scheduled_start and record.scheduled_start > record.scheduled_end:
                raise ValidationError(_("Scheduled end date cannot be before start date"))

    # Method to check actual dates
    @api.constrains('actual_start', 'actual_end')
    def _check_actual_dates(self):
        for record in self:
            if record.actual_end and record.actual_start and record.actual_start > record.actual_end:
                raise ValidationError(_("Actual end date cannot be before start date"))
    
    # Method to submit maintenance request
    def action_submit(self):
        self.ensure_one()
        state_manager = MaintenanceRequestStateManager(self)
        return state_manager.submit()

    # Method to cancel maintenance request
    def action_cancel(self):
        self.ensure_one()
        state_manager = MaintenanceRequestStateManager(self)
        state_manager.cancel()

# Service class for managing state transitions in MaintenanceWorkOrder.
class MaintenanceWorkOrderStateManager:
    def __init__(self, work_order):
        self.work_order = work_order

    # Method to approve work order
    def approve(self):
        work_order = self.work_order
        work_order.state = 'approved'
        # Create execution record after approval.
        execution_vals = {
            'maintenance_request_id': work_order.maintenance_request_id.id,
            'work_order_id': work_order.id,
        }
        work_order.env['maintenance.execution'].create(execution_vals)

        # Update state on related records.
        if work_order.execution_ids:
            work_order.execution_ids.write({'state': 'approved'})
        if work_order.maintenance_request_id:
            work_order.maintenance_request_id.state = 'approved'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action': 'reload_page'},
        }

    # Method to cancel work order
    def cancel(self):
        work_order = self.work_order
        work_order.state = 'cancelled'
        if work_order.execution_ids:
            work_order.execution_ids.write({'state': 'cancelled'})
        if work_order.maintenance_request_id:
            work_order.maintenance_request_id.state = 'cancelled'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action': 'reload_page'},
        }

# Main Maintenace Work Order model
class MaintenanceWorkOrder(models.Model):
    _name = 'maintenance.work.order'
    _inherit = ['base.maintenance']
    _description = 'Maintenance Work Order Creation & Approval'
    _sql_constraints = [
        ('unique_request_work_order', 'unique(maintenance_request_id)', 'A work order already exists for this maintenance request!')
    ]
    _order = 'create_date desc'

    work_order_id = fields.Char(
        string='Work Order ID', required=True, copy=False, readonly=True, default='New'
    )
    maintenance_request_id = fields.Many2one(
        'maintenance.request', ondelete='cascade', string='Maintenance Request', required=True
    )
    assigned_technician = fields.Char(string='Assigned Technician/Service Provider')
    required_parts_ids = fields.One2many('maintenance.required.parts', 'work_order_id', string='Required Parts')
    required_tools_ids = fields.One2many('maintenance.required.tools', 'work_order_id', string='Required Tools')
    planned_hours = fields.Float(string='Planned Hours')
    actual_hours = fields.Float(string='Actual Hours')
    efficiency = fields.Float(compute='_compute_efficiency', store=True)
    estimated_cost = fields.Float(string='Estimated Cost (NPR)')
    approval_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval Status', default='pending', tracking=True)
    approval_authority = fields.Char(string='Approval Authority')
    approval_date = fields.Date(string='Approval Date')
    approval_date_bs = fields.Char(string='Approval Date(BS)', compute='_compute_bs_date', store=True)
    scheduled_maintenance_date = fields.Date(string='Scheduled Maintenance Date')
    scheduled_maintenance_date_bs = fields.Char(string='Scheduled Maintenance Date(BS)', compute='_compute_bs_date', store=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, default=lambda self: self.env.company
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)
    execution_ids = fields.One2many('maintenance.execution', 'work_order_id', string='Executions')

    # Method to compute nepali dates
    @api.depends('scheduled_maintenance_date', 'approval_date')
    def _compute_bs_date(self):
        for record in self:
            record.scheduled_maintenance_date_bs = convert_to_bs_date(record.scheduled_maintenance_date)
            record.approval_date_bs = convert_to_bs_date(record.approval_date)

    # Method to approve work order
    def action_approve(self):
        self.ensure_one()
        state_manager = MaintenanceWorkOrderStateManager(self)
        return state_manager.approve()

    # Method to cancel work order
    def action_cancel(self):
        self.ensure_one()
        state_manager = MaintenanceWorkOrderStateManager(self)
        return state_manager.cancel()

    # Override create method to generate work order id
    @api.model
    def create(self, vals):
        if vals.get('work_order_id', 'New') == 'New' and vals.get('maintenance_request_id'):
            request = self.env['maintenance.request'].browse(vals['maintenance_request_id'])
            if request and request.code:
                request_number = request.code.split('/')[1]
                vals['work_order_id'] = f'WO/{request_number}'
        return super(MaintenanceWorkOrder, self).create(vals)

    # Method to compute efficiency
    @api.depends('planned_hours', 'actual_hours')
    def _compute_efficiency(self):
        for record in self:
            if record.planned_hours and record.actual_hours:
                record.efficiency = (record.planned_hours / record.actual_hours) * 100
            else:
                record.efficiency = 0

# Mixin for validating mechanic contact
class MechanicContactValidationMixin(models.AbstractModel):
    _name = 'mechanic.contact.validation.mixin'
    _description = 'Mixin for validating mechanic contact'

    @api.constrains('mechanic_contact')
    def _check_mechanic_contact(self):
        for record in self:
            if record.mechanic_contact and (
                not record.mechanic_contact.isdigit() or 
                len(record.mechanic_contact) != 10 or 
                not record.mechanic_contact.startswith(('97', '98'))
            ):
                raise ValidationError(
                    _("Mechanic Contact number must be 10 digits long and start with 97 or 98.")
                )

# Service class to manage state transitions and related business logic
class MaintenanceExecutionStateManager:
    def __init__(self, execution):
        self.execution = execution

    # Method to start execution
    def start(self):
        execution = self.execution
        execution.state = 'in_progress'
        if execution.work_order_id:
            execution.work_order_id.state = 'in_progress'
        if execution.maintenance_request_id:
            execution.maintenance_request_id.state = 'in_progress'
            execution.maintenance_request_id.actual_start = fields.Datetime.now()

    # Method to complete execution
    def complete(self):
        execution = self.execution
        execution.state = 'completed'
        if execution.work_order_id:
            execution.work_order_id.state = 'completed'
        if execution.maintenance_request_id:
            execution.maintenance_request_id.state = 'completed'
            execution.maintenance_request_id.actual_end = fields.Datetime.now()
        parts_cost = sum(execution.parts_used_ids.mapped('total_cost'))
        completion_vals = {
            'maintenance_request_id': execution.maintenance_request_id.id,
            'execution_id': execution.id,
            'parts_cost': parts_cost,
        }
        execution.env['maintenance.completion'].create(completion_vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action': 'reload_page'}
        }

    # Method to cancel execution
    def cancel(self):
        execution = self.execution
        execution.state = 'cancelled'
        if execution.work_order_id:
            execution.work_order_id.state = 'cancelled'
        if execution.maintenance_request_id:
            execution.maintenance_request_id.state = 'cancelled'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action': 'reload_page'}
        }

# Main Execution model refactored to delegate responsibilities
class MaintenanceExecution(models.Model, MechanicContactValidationMixin):
    _name = 'maintenance.execution'
    _inherit = ['base.maintenance']
    _description = 'Maintenance Execution & Tracking'
    _sql_constraints = [
        ('unique_request_execution', 'unique(maintenance_request_id)', 
         'An execution record already exists for this maintenance request!')
    ]
    _order = 'create_date desc'

    code = fields.Char(string="Code")
    maintenance_request_id = fields.Many2one(
        'maintenance.request', ondelete='cascade', string='Maintenance Request', required=True
    )
    checklist_ids = fields.One2many(
        'maintenance.checklist.line', 'execution_id', string='Task Checklist'
    )
    parts_used_ids = fields.One2many(
        'maintenance.parts.used', 'execution_id', string='Parts Used'
    )
    labor_time_ids = fields.One2many(
        'maintenance.labor.time', 'execution_id', string='Labor Time'
    )
    quality_check_passed = fields.Boolean('Quality Check Passed')
    quality_notes = fields.Text('Quality Notes')
    safety_checklist_completed = fields.Boolean('Safety Checklist Completed')
    safety_issues_noted = fields.Text('Safety Issues')
    service_duration = fields.Float(
        string='Service Duration (Hours)', help="Duration in hours"
    )
    mechanic_name = fields.Char(string='Mechanic Name')
    mechanic_contact = fields.Char(string='Mechanic Contact', size=10)
    issues_found = fields.Text(string='Issues Found')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, default=lambda self: self.env.company
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)
    work_order_id = fields.Many2one('maintenance.work.order', string='Work Order')
    completion_ids = fields.One2many(
        'maintenance.completion', 'execution_id', string='Completion'
    )

    # Method to start execution
    def action_start(self):
        self.ensure_one()
        state_manager = MaintenanceExecutionStateManager(self)
        state_manager.start()

    # Method to complete execution
    def action_complete(self):
        self.ensure_one()
        state_manager = MaintenanceExecutionStateManager(self)
        return state_manager.complete()

    # Method to cancel execution
    def action_cancel(self):
        self.ensure_one()
        state_manager = MaintenanceExecutionStateManager(self)
        return state_manager.cancel()

    # Overriding the default create method to set the execution code
    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New' and vals.get('maintenance_request_id'):
            request = self.env['maintenance.request'].browse(vals['maintenance_request_id'])
            if request and request.code:
                request_number = request.code.split('/')[1]
                vals['code'] = f'EXE/{request_number}'
        return super(MaintenanceExecution, self).create(vals)

# Maintenance Completion model
class MaintenanceCompletion(models.Model):
    _name = 'maintenance.completion'
    _inherit = ['base.maintenance']
    _description = 'Maintenance Completion & Reporting'
    _sql_constraints = [
        ('unique_request_completion', 'unique(maintenance_request_id)', 'A completion record already exists for this maintenance request!')
    ]
    _order = 'create_date desc'

    maintenance_request_id = fields.Many2one('maintenance.request', ondelete='cascade', string='Maintenance Request', required=True)
    parts_cost = fields.Float('Parts Cost')
    labor_cost = fields.Float('Labor Cost')
    additional_costs = fields.Float('Additional Costs')
    total_cost = fields.Float(compute='_compute_total_cost', store=True)
    downtime_hours = fields.Float('Total Downtime Hours')
    mttr = fields.Float('Mean Time To Repair', compute='_compute_mttr')
    quality_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor')
    ])
    invoice_details = fields.Text(string='Invoice Details')
    payment_status = fields.Selection([
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial')
    ], string='Payment Status')
    maintenance_report = fields.Text(string='Maintenance Report')
    next_maintenance_due_date = fields.Date(string='Next Maintenance Due Date')
    vehicle_number = fields.Char(string="Vehicle Number", related='maintenance_request_id.vehicle_id.final_number', store=True)
    date_bs = fields.Char(string="Next Maintenance Due Date", compute='_compute_nepali_dates', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    mttr = fields.Float(
        string='Mean Time To Repair (Hours)', 
        compute='_compute_mttr',
        store=True,
        help="Mean Time To Repair - calculated from maintenance start to completion"
    )
    execution_id = fields.Many2one('maintenance.execution', string='Executions')
    
    # Method to compute mean time to repair
    @api.depends('maintenance_request_id.actual_start', 'maintenance_request_id.actual_end')
    def _compute_mttr(self):
        for record in self:
            if record.maintenance_request_id and record.maintenance_request_id.actual_start and record.maintenance_request_id.actual_end:
                delta = record.maintenance_request_id.actual_end - record.maintenance_request_id.actual_start
                record.mttr = delta.total_seconds() / 3600
            else:
                record.mttr = 0.0

    # Method to compute total cost
    @api.depends('parts_cost', 'labor_cost', 'additional_costs')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = record.parts_cost + record.labor_cost + record.additional_costs

# Supporting Models
class MaintenanceChecklist(models.Model):
    _name = 'maintenance.checklist.line'
    _description = 'Maintenance Checklist Line'

    execution_id = fields.Many2one('maintenance.execution', ondelete='cascade')
    task = fields.Char('Task')
    completed = fields.Boolean('Completed')
    notes = fields.Text('Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

class MaintenancePartsUsed(models.Model):
    _name = 'maintenance.parts.used'
    _description = 'Parts Used in Maintenance'

    execution_id = fields.Many2one('maintenance.execution', ondelete='cascade')
    part_name = fields.Char(string='Part Name')
    quantity = fields.Float('Quantity')
    unit_cost = fields.Float('Unit Cost')
    total_cost = fields.Float(compute='_compute_total')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('quantity', 'unit_cost')
    def _compute_total(self):
        for record in self:
            record.total_cost = record.quantity * record.unit_cost

class MaintenanceRequiredParts(models.Model):
    _name = 'maintenance.required.parts'
    _description = 'Required Parts for Maintenance'

    work_order_id = fields.Many2one('maintenance.work.order', ondelete='cascade')
    part_name = fields.Char(string='Part Name')
    quantity = fields.Float('Required Quantity')
    available_quantity = fields.Float('Available Quantity')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

class MaintenanceRequiredTools(models.Model):
    _name = 'maintenance.required.tools'
    _description = 'Required Tools for Maintenance'

    work_order_id = fields.Many2one('maintenance.work.order', ondelete='cascade')
    tool_name = fields.Char(string='Tool Name')
    quantity = fields.Float('Required Quantity')
    available = fields.Boolean('Available')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

class MaintenanceLaborTime(models.Model):
    _name = 'maintenance.labor.time'
    _description = 'Labor Time Tracking'

    execution_id = fields.Many2one('maintenance.execution', ondelete='cascade')
    technician_name = fields.Char(string='Technician Name')
    start_time = fields.Date('Start Time')
    end_time = fields.Date('End Time')
    hours = fields.Float(compute='_compute_hours', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('start_time', 'end_time')
    def _compute_hours(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.hours = delta.days * 24
            else:
                record.hours = 0.0