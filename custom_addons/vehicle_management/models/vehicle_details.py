from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import os
from werkzeug.urls import url_quote
import logging
import base64
import nepali_datetime
from datetime import time, datetime, timedelta
import re
from ..utils.dashboard_notification import Utilities 
from ..models.maintenance_management import convert_to_bs_date
_logger = logging.getLogger(__name__)

# Base Vehicle Document Class
class BaseVehicleDocument(models.AbstractModel):
    _name = 'base.vehicle.document'
    _description = 'Base Vehicle Document'

    company_id = fields.Many2one('res.company', string='Company Name', required=True, default=lambda self: self.env.company)
    vehicle_company_id = fields.Many2one('custom.vehicle.company', string='Vehicle Company', required=True)
    owner_id = fields.Many2one('custom.vehicle.owner', string='Vehicle Owner', required=True, domain="[('vehicle_company_id', '=', vehicle_company_id)]")
    vehicle_number = fields.Many2one('vehicle.number', string='Vehicle Number', required=True)
    last_renewal_date = fields.Date(string='Last Renewal Date', required=True)
    last_renewal_date_bs = fields.Char(string='Last Renewal Date (Nepali)', store=True,compute = "_compute_nepali_dates")
    expiry_date = fields.Date(string='Expiry Date', required=True)
    expiry_date_bs = fields.Char(string='Expiry Date (Nepali)', store=True,compute = "_compute_nepali_dates")
    vehicle_number_domain = fields.Char(compute="_compute_vehicle_number_domain", store=False)
    renewed = fields.Boolean(string='Renewed Status', default=False)
    renewal_cost = fields.Float(string='Renewal Cost', required=True)

    fine_cost = fields.Float(string="Fine Cost")
    total_cost = fields.Float(string="Total Cost",compute = "_compute_total_cost",store="True")
    
    # Method to compute total cost
    @api.depends('fine_cost','renewal_cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = record.fine_cost + record.renewal_cost
            
    # Method to compute nepali dates
    @api.depends('last_renewal_date', 'expiry_date')
    def _compute_nepali_dates(self):
        for record in self:
            record.last_renewal_date_bs = convert_to_bs_date(record.last_renewal_date)
            record.expiry_date_bs = convert_to_bs_date(record.expiry_date)

    # Method to compute vehicle number domain
    @api.depends('owner_id')
    def _compute_vehicle_number_domain(self):
        for record in self:
            if record.owner_id:
                vehicle_ids = record.owner_id.vehicle_number.ids
                record.vehicle_number_domain = [('id', 'in', vehicle_ids)]
            else:
                record.vehicle_number_domain = [('id', 'in', [])]

    # Method to create due details
    def _create_due_details(self, document_type, extra_vals=None):
        self.ensure_one()
        vals = {
            'company_id': self.company_id.id,
            'vehicle_company_id': self.vehicle_company_id.id,
            'vehicle_number': self.vehicle_number.id,
            'expiry_date': self.expiry_date,
            'expiry_date_bs': self.expiry_date_bs,
            'renewal_date': self.last_renewal_date,
            'renewal_date_bs': self.last_renewal_date_bs,
            'due_status': 'completed' if self.renewed else 'due',
            'renewal_cost': self.renewal_cost,
            'due_details_name': document_type,
            f'{document_type}_id': self.id,
        }
        if extra_vals:
            vals.update(extra_vals)
        return self.env['vehicle.due.details'].create(vals)

# Base Document Attachment Model
class BaseDocumentAttachment(models.AbstractModel):
    _name = 'base.document.attachment'
    _description = 'Base Document Attachment'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    type_id = fields.Many2one("document.type", string="Document Type")
    documents = fields.Binary(string="Documents")
    file_name = fields.Char(string="File Name")
    preview = fields.Html(string="Document Preview", compute="_compute_preview", sanitize=False, store=True)
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif"}

    # Method to validate file extension
    def _validate_file_extension(self, file_name):
        if not file_name:
            return
        file_extension = os.path.splitext(file_name)[1][1:].lower()
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise ValidationError("Invalid file type! Only PDF, PNG, JPG, JPEG, and GIF files are allowed.")

    # Method to compute preview
    @api.depends("documents", "file_name")
    def _compute_preview(self):
        for record in self:
            if not record.documents or not record.file_name:
                record.preview = '<div>No file</div>'
                continue

            file_extension = os.path.splitext(record.file_name)[1][1:].lower()
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

            if file_extension == "pdf":
                file_url = f"{base_url}/web/content?model={self._name}&id={record.id}&field=documents&filename={record.file_name}"
                record.preview = f"""
                    <div style="text-align: center;">
                        <a href="{file_url}" target="_blank" class="btn btn-primary">
                            <i class="fa fa-file-pdf-o"/> View PDF
                        </a>
                    </div>
                """
            elif file_extension in ["png", "jpg", "jpeg", "gif"]:
                image_url = f"{base_url}/web/image?model={self._name}&id={record.id}&field=documents&filename={record.file_name}"
                record.preview = f"""
                    <div style="text-align: center;">
                        <a href="{image_url}" target="_blank">
                            <img src="{image_url}" style="max-height: 50px; max-width: 100px; object-fit: contain;"/>
                        </a>
                    </div>
                """
            else:
                record.preview = '<div>Unsupported file type</div>'

    # Override create method to compute preview
    @api.model
    def create(self, vals):
        if 'file_name' in vals:
            self._validate_file_extension(vals.get("file_name"))
        res = super().create(vals)
        if 'documents' in vals or 'file_name' in vals:
            res._compute_preview()
        return res

    # Override write method to compute preview
    def write(self, vals):
        if 'file_name' in vals:
            self._validate_file_extension(vals.get("file_name"))
        res = super().write(vals)
        if 'documents' in vals or 'file_name' in vals:
            self._compute_preview()
        return res

# Custom Vehicle Bluebook Model
class CustomVehicleBluebook(models.Model):
    _name = 'custom.vehicle.bluebook'
    _inherit = 'base.vehicle.document'
    _description = 'Custom Vehicle Bluebook'

    bluebook_document_ids = fields.One2many("bluebook.document", "document_id")
    due_details = fields.One2many('vehicle.due.details', 'bluebook_id', string='Due Details')

    # Method to send notifications
    def sendNotifications(self):
        today = datetime.today().date()
        today_bs = nepali_datetime.date.from_datetime_date(today)
        seven_days = today_bs + timedelta(days=7)
        for record in self.search([]):
            expiry_date = nepali_datetime.date.from_datetime_date(record.expiry_date)
            utilities = Utilities(self.env)
            if today_bs <= expiry_date <= seven_days:
                expiry_date = record.expiry_date_bs
                vehicle_number = record.vehicle_number.final_number
                utilities.showNotificationDashboard(date = expiry_date, vehicle_number = vehicle_number,renewal_type = 'bluebook', driver_name = None)

    # Method to compute the upcoming expiry date
    @api.depends('expiry_date_bs')
    def compute_is_upcoming_expiry(self):
       
        today = fields.Date.today()
        today_bs = nepali_datetime.date.from_datetime_date(today)
        future_date_obj = today_bs + timedelta(days=30)
        for record in self:
          
            if record.vehicle_number and record.expiry_date_bs:
                year, month, day = map(int, record.expiry_date_bs.split('-'))
                expiry_date_obj = nepali_datetime.date(year, month, day)
                record.vehicle_number.write({
                    'is_upcoming_expiry': today_bs <= expiry_date_obj <= future_date_obj
                })

    # Override create method to compute upcoming expiry and create due details
    @api.model
    def create(self, vals):
        records = super().create(vals)
        for record in records:
            record.compute_is_upcoming_expiry()
            record._create_due_details('bluebook')
        return records

    # Override write method to compute upcoming expiry and update due details
    def write(self, vals):
        success = super().write(vals)
        if not success:
            return False
        for record in self:
            due_details_record = self.env['vehicle.due.details'].search([
                ('bluebook_id', '=', record.id)
            ], limit=1)
            if due_details_record:
                due_details_record.write({
                    'company_id': record.company_id.id,
                    'vehicle_company_id': record.vehicle_company_id.id,
                    'vehicle_number': record.vehicle_number.id,
                    'expiry_date': record.expiry_date,
                    'expiry_date_bs': record.expiry_date_bs,
                    'renewal_date': record.last_renewal_date,
                    'renewal_date_bs': record.last_renewal_date_bs,
                    'due_status': 'completed' if record.renewed else 'due',
                    'renewal_cost': record.renewal_cost,
                })
        return True

# Custom Vehicle Permit Model
class CustomVehiclePermit(models.Model):
    _name = 'custom.vehicle.permit'
    _inherit = 'base.vehicle.document'
    _description = 'Custom Vehicle Permit'

    permit_document_ids = fields.One2many("permit.document", "document_id")
    due_details = fields.One2many('vehicle.due.details', 'permit_id', string='Due Details')
    
    # Method to send notifications
    def sendNotifications(self):
        today = datetime.today().date()
        today_bs = nepali_datetime.date.from_datetime_date(today)
        seven_days = today_bs + timedelta(days=7)
        for record in self.search([]):
            expiry_date = nepali_datetime.date.from_datetime_date(record.expiry_date)
            utilities = Utilities(self.env)
            if today_bs <= expiry_date <= seven_days:
                expiry_date = record.expiry_date_bs
                vehicle_number = record.vehicle_number.final_number
                utilities.showNotificationDashboard(date = expiry_date, vehicle_number = vehicle_number,renewal_type = 'permit', driver_name = None)

    # Method to compute the upcoming expiry date
    @api.depends('expiry_date_bs')
    def compute_is_upcoming_expiry(self):
        today = fields.Date.today()
        today_bs = nepali_datetime.date.from_datetime_date(today)
        future_date_obj = today_bs + timedelta(days=30)
        for record in self:
            if record.vehicle_number and record.expiry_date_bs:
                year, month, day = map(int, record.expiry_date_bs.split('-'))
                expiry_date_obj = nepali_datetime.date(year, month, day)
                record.vehicle_number.write({
                    'upcoming_permit_expiry': today_bs <= expiry_date_obj <= future_date_obj
                })

    # Override create method to compute upcoming expiry and create due details
    @api.model
    def create(self, vals):
        records = super().create(vals)
        for record in records:
            record.compute_is_upcoming_expiry()
            record._create_due_details('permit')
        return records

# Custom Vehicle Pollution Model
class CustomVehiclePollution(models.Model):
    _name = 'custom.vehicle.pollution'
    _inherit = 'base.vehicle.document'
    _description = 'Custom Vehicle Pollution'

    pollution_document_ids = fields.One2many("pollution.document", "document_id")
    due_details = fields.One2many('vehicle.due.details', 'pollution_id', string='Due Details')

    # Method to compute the upcoming expiry date
    @api.depends('expiry_date_bs')
    def compute_is_upcoming_expiry(self):
        today = fields.Date.today()
        today_bs = nepali_datetime.date.from_datetime_date(today)
        future_date_obj = today_bs + timedelta(days=30)
        for record in self:
            if record.vehicle_number and record.expiry_date_bs:
                year, month, day = map(int, record.expiry_date_bs.split('-'))
                expiry_date_obj = nepali_datetime.date(year, month, day)
                record.vehicle_number.write({
                    'upcoming_pollution_expiry': today_bs <= expiry_date_obj <= future_date_obj
                })
    
    # Method to send notifications
    def sendNotifications(self):
        today = datetime.today().date()
        today_bs = nepali_datetime.date.from_datetime_date(today)
        seven_days = today_bs + timedelta(days=7)
        for record in self.search([]):
            expiry_date = nepali_datetime.date.from_datetime_date(record.expiry_date)
            utilities = Utilities(self.env)
            if today_bs <= expiry_date <= seven_days:
                expiry_date = record.expiry_date_bs
                vehicle_number = record.vehicle_number.final_number
                utilities.showNotificationDashboard(date = expiry_date, vehicle_number = vehicle_number,renewal_type = 'pollution', driver_name = None)

    # Override create method to compute upcoming expiry and create due details
    @api.model
    def create(self, vals):
        records = super().create(vals)
        for record in records:
            record.compute_is_upcoming_expiry()
            record._create_due_details('pollution')
        return records

# Custom Vehicle Insurance Model
class CustomVehicleInsurance(models.Model):
    _name = 'custom.vehicle.insurance'
    _inherit = 'base.vehicle.document'
    _description = 'Custom Vehicle Insurance'

    insurance_company = fields.Char(string='Insurance Company')
    insurance_policy_number = fields.Char(string='Insurance Policy Number')
    bill_arrived = fields.Boolean(string='Bill Arrived')
    insurance_document_ids = fields.One2many("insurance.document", "document_id")
    due_details = fields.One2many('vehicle.due.details', 'insurance_id', string='Due Details')

    # Method to send notifications
    def sendNotifications(self):
        today = datetime.today().date()
        today_bs = nepali_datetime.date.from_datetime_date(today)
        seven_days = today_bs + timedelta(days=7)
        for record in self.search([]):
            expiry_date = nepali_datetime.date.from_datetime_date(record.expiry_date)
            utilities = Utilities(self.env)
            if today_bs <= expiry_date <= seven_days:
                expiry_date = record.expiry_date_bs
                vehicle_number = record.vehicle_number.final_number
                utilities.showNotificationDashboard(date = expiry_date, vehicle_number = vehicle_number,renewal_type = 'insurance', driver_name = None)

    # Method to compute the upcoming expiry date
    @api.depends('expiry_date_bs')
    def compute_is_upcoming_expiry(self):
        today = fields.Date.today()
        today_bs = nepali_datetime.date.from_datetime_date(today)
        future_date_obj = today_bs + timedelta(days=30)
        for record in self:
            if record.vehicle_number and record.expiry_date_bs:
                year, month, day = map(int, record.expiry_date_bs.split('-'))
                expiry_date_obj = nepali_datetime.date(year, month, day)
                record.vehicle_number.write({
                    'upcoming_insurance_expiry': today_bs <= expiry_date_obj <= future_date_obj
                })

    # Override create method to compute upcoming expiry and create due details
    @api.model
    def create(self, vals):
        records = super().create(vals)
        for record in records:
            record.compute_is_upcoming_expiry()
            extra_vals = {
                'insurance_company': record.insurance_company,
                'insurance_policy_number': record.insurance_policy_number,
            }
            record._create_due_details('insurance', extra_vals)
        return records

# Document Attachment Classes
# Bluebook 
class BluebookDocument(models.Model):
    _name = 'bluebook.document'
    _inherit = 'base.document.attachment'
    _description = 'Bluebook Document'

    document_id = fields.Many2one("custom.vehicle.bluebook", string="Registration")

# Permit
class PermitDocument(models.Model):
    _name = 'permit.document'
    _inherit = 'base.document.attachment'
    _description = 'Permit Document'

    document_id = fields.Many2one("custom.vehicle.permit", string="Registration")

# Pollution
class PollutionDocument(models.Model):
    _name = 'pollution.document'
    _inherit = 'base.document.attachment'
    _description = 'Pollution Document'

    document_id = fields.Many2one("custom.vehicle.pollution", string="Registration")

# Insurance
class InsuranceDocument(models.Model):
    _name = 'insurance.document'
    _inherit = 'base.document.attachment'
    _description = 'Insurance Document'

    document_id = fields.Many2one("custom.vehicle.insurance", string="Registration")
    
# Driver Training Document Model 
class DriverTrainingDocument(models.Model):
    _name = 'training.document'
    _inherit = 'base.document.attachment'
    _description = 'Insurance Document'

    document_id = fields.Many2one("driver.training", string="Training Document")

# Fine Details
class FineDocument(models.Model):
    _name = 'fine.document'
    _inherit = 'base.document.attachment'
    _description = 'Insurance Document'

    document_id = fields.Many2one("fine.details", string="Fine Document")
    
# Document Type Model
class DocumentType(models.Model):
    _name = "document.type"
    _description = "Document Type"
    _rec_name = "name"

    name = fields.Char(string="Document Name")
    code = fields.Char(string="Code")

# Custom Vehicle Owner Model
class CustomVehicleOwner(models.Model):
    _name = 'custom.vehicle.owner'
    _description = 'Custom Vehicle Owner'

    company_id = fields.Many2one('res.company', string='Company Name', required=True, default=lambda self: self.env.company)
    vehicle_company_id = fields.Many2one('custom.vehicle.company', string='Vehicle Company', required=True)
    name = fields.Char(string='Owner Name', required=True)
    address = fields.Char(string='Address')
    phone = fields.Char(string='Phone Number', size=10)
    vehicle_number = fields.Many2many('vehicle.number', string='Vehicle IDs')
    email = fields.Char(string='Email')
    
    # Method to check email format
    @api.constrains('email')
    def _check_email_format(self):
        for record in self:
            if record.email and not re.match(r"[^@]+@[^@]+\.[^@]+", record.email):
                raise ValidationError("Invalid email format.")

    # Method to check mobile number
    @api.constrains('phone')
    def _check_mobile_length_and_prefix(self):
        for record in self:
            if record.phone and (not record.phone.isdigit() or len(record.phone) != 10 or not record.phone.startswith(('97', '98'))):
                raise ValidationError("Phone number must be 10 digits long and start with 97 or 98.")

    # Override create method to write vehicle owner and vehicle ids in vehicle company and vehicle number
    @api.model
    def create(self, vals):
        new_record = super().create(vals)
        if new_record.vehicle_company_id:
            new_record.vehicle_company_id.write({
                'vehicle_owner_ids': [(4, new_record.id)],
                'vehicle_ids': [(4, vehicle.id) for vehicle in new_record.vehicle_number],
            })
        if new_record.vehicle_number:
            new_record.vehicle_number.write({
                'vehicle_owner': new_record.id,
                'vehicle_company': new_record.vehicle_company_id.id,
            })
        return new_record

    # Override write method to write vehicle owner and vehicle ids in vehicle company and vehicle number
    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.vehicle_company_id:
                record.vehicle_company_id.write({
                    'vehicle_owner_ids': [(4, record.id)],
                    'vehicle_ids': [(4, vehicle.id) for vehicle in record.vehicle_number],
                })
            if record.vehicle_number:
                record.vehicle_number.write({
                    'vehicle_owner': record.id,
                    'vehicle_company': record.vehicle_company_id.id,
                })
        return res

# Custom Vehicle Company Model
class CustomVehicleCompany(models.Model):
    _name = 'custom.vehicle.company'
    _description = 'Custom Vehicle Company'
    _rec_name = 'company_name'

    company_name = fields.Char(string="Vehicle Company Name:")
    name_np = fields.Char(string="Vehicle Company Name(NP):")
    vehicle_owner_ids = fields.Many2many('custom.vehicle.owner', string='Vehicle Owners')
    vehicle_ids = fields.Many2many('vehicle.number', string='Vehicles')
    company_address = fields.Char(string='Company Address')
    contact_person = fields.Char(string='Contact Person')
    phone = fields.Char(string='Contact Phone', size=10)
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.uid, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    # Method to translate company name
    @api.onchange("company_name", "name_np")
    def _onchange_company_name(self):
        if self.company_name:
            translation_model = self.env['translation.service.mixin']
            self.name_np = translation_model.translate_to_nepali(self.company_name)
        elif self.name_np:
            translation_model = self.env['translation.service.mixin']
            self.company_name = translation_model.translate_to_english(self.name_np)

    # Method to check mobile number
    @api.constrains('phone')
    def _check_phone_format(self):
        for record in self:
            if record.phone and (not record.phone.isdigit() or len(record.phone) != 10 or not record.phone.startswith(('97', '98'))):
                raise ValidationError("Phone number must be 10 digits long and start with 97 or 98.")

    # Override name_get method
    def name_get(self):
        result = []
        for record in self:
            name = record.company_name or ''
            result.append((record.id, name))
        return result