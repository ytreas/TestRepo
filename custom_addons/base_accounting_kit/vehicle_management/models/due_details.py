from odoo import models, fields, api
from datetime import datetime,timedelta
import nepali_datetime


def parse_nepali_date(nepali_date_str):
    year, month, day = map(int, nepali_date_str.split('-'))
    return (year, month, day)
def gregorian_to_nepali(gregorian_date):
    # This conversion logic depends on your specific conversion method
    # In a simple case, you may need to approximate or find a library that does this conversion
    # Here we will just return a tuple for comparison
    # This is a placeholder example, adjust it according to your actual conversion logic.
    return (gregorian_date.year, gregorian_date.month, gregorian_date.day)   
class CustomVehicleDueDetails(models.Model):
    _name = 'vehicle.due.details'
    _description = 'Custom Vehicle Due Details'
    
    company_id = fields.Many2one('res.company', string='Company Name', default=lambda self: self.env.company)
    vehicle_company_id = fields.Many2one('custom.vehicle.company', string='Vehicle Company')
    vehicle_number = fields.Many2one('vehicle.number', string='Vehicle Number', required=True, ondelete='cascade')
    expiry_date = fields.Date(string='Expiry Date', required=True)
    renewal_date = fields.Date(string='Renewal Date', required=True)
    renewal_date_bs = fields.Char(string='Renewal Date (Nepali)', compute='_compute_nepali_dates', store=True)
    expiry_date_bs = fields.Char(string='Expiry Date (Nepali)', compute='_compute_nepali_dates', store=True)
    due_status = fields.Selection([
        ('due', 'Due'),
        ('overdue', 'Overdue'),
        ('upcoming', 'Upcoming'),
        ('completed', 'Completed')
    ], string='Due Status', default='due', required=True)
    renewal_cost = fields.Float(string='Renewal Cost', required=True)
    remarks = fields.Text(string='Remarks')
    notification_settings = fields.Boolean(string='Notification Settings', default=True)

    # documents_type = fields.Many2one('documents.type', string='Documents Type')
    # document = fields.Binary(string="Documents upload")
    bluebook_id = fields.Many2one('custom.vehicle.bluebook',string="Bluebook")
    permit_id = fields.Many2one('custom.vehicle.permit',string="Permit")
    pollution_id = fields.Many2one('custom.vehicle.pollution',string="Pollution")
    insurance_id = fields.Many2one('custom.vehicle.insurance',string="Insurance") 
    due_details_name = fields.Selection([
        ('bluebook', 'Bluebook'),
        ('pollution', 'Pollution'),
        ('insurance', 'Insurance'),
        ('permit', 'Permit')
    ], string='Due Name')
    insurance_company = fields.Char(string='Insurance Company')
    insurance_policy_number = fields.Char(string='Insurance Policy Number')
    payment_status = fields.Boolean(
        string='Payment status', 
        default= False
        
    )
    

    
    # bluebook_expiry_date_bs = fields.Char(string='Bluebook Expiry Date (Nepali)', related='bluebook_id.expiry_date_bs', store=True)


    @api.model
    def get_latest_record(self, vehicle_number, due_details_name):
        """Retrieve the latest record based on vehicle_number and due_details_name."""
        latest_record = self.search([
            ('vehicle_number', '=', vehicle_number),
            ('due_details_name', '=', due_details_name)
        ], order='expiry_date desc', limit=1)
        # print("44444444444444444444",latest_record.vehicle_number.final_number)
        return latest_record

    def name_get(self):
        result = []
        for record in self:
            # You can concatenate multiple fields or choose a specific one for display
            name = f"{record.vehicle_number.final_number} - {record.due_details_name.capitalize()} - {record.renewal_date}"
            result.append((record.id, name))
        return result
    # @api.onchange('bluebook_id')
    # def _onchange_vehicle_number(self):
    #     print("@@@@@@@@@@@@@@@@@@@@@@@",self.bluebook_id.vehicle_number)
    #     # Set the vehicle_number in the vehicle.due.details to be the same as the one in bluebook form
    #     if self.bluebook_id:
    #         for bluebook_id in self.bluebook_id:
    #             self.vehicle_number = bluebook_id.vehicle_number.id
  

    @api.depends('expiry_date', 'renewal_date')
    def _compute_nepali_dates(self):
        # print("######################")
        for record in self:
            if record.expiry_date:
                expiry_nepali_date = nepali_datetime.date.from_datetime_date(record.expiry_date)
                record.expiry_date_bs = expiry_nepali_date.strftime('%Y-%m-%d')
                # print("######################",record.expiry_date_bs)
            else:
                record.expiry_date_bs = False

            if record.renewal_date:
                renewal_nepali_date = nepali_datetime.date.from_datetime_date(record.renewal_date)
                record.renewal_date_bs = renewal_nepali_date.strftime('%Y-%m-%d')
            else:
                record.renewal_date_bs = False



class customFineAndPenalty(models.Model):
    _name = 'custom.fine.penalty'
    _description = 'Custom Fine and Penalty'

    company_id = fields.Many2one('res.company', string='Company Name', required=True, default=lambda self: self.env.company)
    driver_id = fields.Many2one('driver.details', string='Driver', required=True)
    vehicle_company_id = fields.Many2one('custom.vehicle.company', string='Vehicle Company', required=True)
    vehicle_number = fields.Many2one('vehicle.number', string='Vehicle Number', required=True, ondelete='cascade')
    fine_date = fields.Date(string='Fine Date', required=True)
    fine_date_bs = fields.Char(string='Fine Date (Nepali)', compute='_compute_nepali_date', store=True)

    details_id = fields.One2many('fine.details', 'fine_id',string='Fine Details')

    fine_name = fields.Text(string='Fine Name', compute='_concat_finename', store=True)

    date_bs = fields.Char(string='Date (BS)', compute='_compute_nepali_date', store=True)

    total_fine = fields.Float(string='Total Fine', compute='_compute_total_cost', store=True)
    
    is_today = fields.Boolean(string='Is Today', compute='_compute_filter_value', store=True)
    this_week = fields.Boolean(string='This Week', compute='_compute_filter_value', store=True)
    this_month = fields.Boolean(string='This Month', compute='_compute_filter_value', store=True)
    driver_performance = fields.Many2one('driver.performance')
    @api.depends('fine_date')
    def _compute_filter_value(self):
        for record in self:
            if record.fine_date_bs:
                today = datetime.now().date()

                today_nepali_date = nepali_datetime.date.from_datetime_date(today)
                # days_to_sunday = (today_nepali_date.weekday() + 1) % 7  # for english
                days_to_sunday = nepali_datetime.date.weekday(today_nepali_date)
                
                start_of_week = today_nepali_date - timedelta(days=days_to_sunday)
                start_of_month = today_nepali_date.replace(day=1)
                
                fine_date_bs_nepali = parse_nepali_date(record.fine_date_bs)
                today_nepali_date_bs = gregorian_to_nepali(today_nepali_date)
                start_of_week_nepali = gregorian_to_nepali(start_of_week)
                start_of_month_nepali = gregorian_to_nepali(start_of_month)
                
                record.is_today = fine_date_bs_nepali == today_nepali_date_bs
                record.this_week = start_of_week_nepali <= fine_date_bs_nepali <= today_nepali_date_bs
                record.this_month = fine_date_bs_nepali >= start_of_month_nepali
            else:
                record.is_today = False
                record.this_week = False
                record.this_month = False
      
                
    def _change_filter_value(self):
        penalty_records = self.env['custom.fine.penalty'].search([])
        for record in penalty_records:
            if record.fine_date_bs:
                today = datetime.now().date()

                today_nepali_date = nepali_datetime.date.from_datetime_date(today)
                # today_nepali_date_str = "2082-12-14"
                # today_nepali_date_test = datetime.strptime(today_nepali_date_str, "%Y-%m-%d").date()
                # print("######################",today_nepali_date_test,type(today_nepali_date_test),)
               
                print("Type",nepali_datetime.date.weekday(today_nepali_date))
                # days_to_sunday = (today_nepali_date.weekday() + 1) % 7  # for english
                days_to_sunday = nepali_datetime.date.weekday(today_nepali_date)
                
                start_of_week = today_nepali_date - timedelta(days=days_to_sunday)
                start_of_month = today_nepali_date.replace(day=1)
                
                fine_date_bs_nepali = parse_nepali_date(record.fine_date_bs)
                today_nepali_date_bs = gregorian_to_nepali(today_nepali_date)
                start_of_week_nepali = gregorian_to_nepali(start_of_week)
                start_of_month_nepali = gregorian_to_nepali(start_of_month)
                
                record.is_today = fine_date_bs_nepali == today_nepali_date_bs
                record.this_week = start_of_week_nepali <= fine_date_bs_nepali <= today_nepali_date_bs
                record.this_month = fine_date_bs_nepali >= start_of_month_nepali
            else:
                record.is_today = False
                record.this_week = False
                record.this_month = False               
    @api.depends('details_id')
    def _concat_finename(self):
        for record in self:
            fine_names = []
            for detail in record.details_id:
                fine_name = f"{detail.fine_type.name or ''} - {detail.fine_status or ''}"
                fine_names.append(fine_name)
            # Concatenate all fine names with a separator (e.g., newline or comma)
            record.fine_name = '\n'.join(fine_names)
            
    @api.depends('fine_date')
    def _compute_nepali_date(self):
        for record in self:
            if record.fine_date:
                fine_nepali_date = nepali_datetime.date.from_datetime_date(record.fine_date)
                record.fine_date_bs = fine_nepali_date.strftime('%Y-%m-%d')
                record.date_bs = fine_nepali_date.strftime('%Y-%m-%d')
            else:
                record.fine_date_bs = False


    @api.depends('details_id.fine_amount')
    def _compute_total_cost(self):
        for record in self:
            total_cost = sum(line.fine_amount for line in record.details_id)
            record.total_fine = total_cost or 0.0



class FineDetails(models.Model):
    _name = 'fine.details'
    _description ='Fine Details Description'

    fine_id = fields.Many2one('custom.fine.penalty',string='Fine')
    fine_type = fields.Many2one('violations.type',string='Fine Type')
    fine_amount = fields.Float(string='Fine Amount', required=True)
    fine_reason = fields.Text(string='Fine Reason')
    fine_status = fields.Selection([
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('overdue', 'Overdue')
    ], string='Payment Status', default='unpaid', required=True)
    notification_settings = fields.Boolean(string='Notification Settings', default=True)
    payment_due_date = fields.Date(string='Payment Due Date', required=True)
    payment_due_date_bs = fields.Char(string='Payment Due Date (Nepali)', compute='_compute_nepali_date', store=True)
    issued_by = fields.Char(string='Issued By', required=True)
    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    fine_document_ids = fields.One2many("fine.document", "document_id")


    @api.depends('payment_due_date')
    def _compute_nepali_date(self):
        for record in self:
            if record.payment_due_date:
                payement_due_nepali_date = nepali_datetime.date.from_datetime_date(record.payment_due_date)
                record.payment_due_date_bs = payement_due_nepali_date.strftime('%Y-%m-%d')
            else:
                record.payment_due_date_bs = False