from odoo import api,fields, models, _
from datetime import datetime
from datetime import time, datetime, timedelta
from pytz import timezone
from odoo.exceptions import ValidationError
import nepali_datetime

class DailyArrivalEntry(models.Model):
    _name = 'amp.daily.arrival.entry'
    _description = 'Daily Arrival Entry'
    
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    arrival_date = fields.Date(string='Arrival Date',required=True, default=fields.Date.context_today)
    arrival_date_bs = fields.Char(string='Arrival Date (Nepali)', compute='_compute_nepali_dates', store=True)

    # check_out_date = fields.Date(string='Check Out Date')
    # check_out_date_bs = fields.Char(string='Check Out Date (Nepali)', compute='_compute_nepali_dates', store=True)
    
    
    # mobile_number = fields.Char(string='Mobile Number',size =10)

    commodity_id = fields.One2many('amp.commodity','am_daily_id', string='Commodity', required=True)
    # volume = fields.Float(string='Volume', required=True, related='vehicle_type.max_weight')

    default_vehicle_number = fields.Many2one('vehicle.number',string='Vehicle Number')
    check_out_date = fields.Char(string='Check Out Date',related='default_vehicle_number.check_out_date_bs')
    check_in_date = fields.Char(string='Check In Date',related='default_vehicle_number.check_in_date_bs')
    check_in_time = fields.Char(string='Check In Time',related='default_vehicle_number.check_in_time')
    check_out_time = fields.Char(string='Check Out Time',related='default_vehicle_number.check_out_time')
    paid_boolean =fields.Boolean(string='Paid',related='default_vehicle_number.paid_bool')

    line_total = fields.Float(string="Total Commodity Volume:", compute = '_compute_total_volume')
    # state = fields.Selection([('draft','Draft'),('check_in','Check In'),('check_out','Check Out'),('payment','Payment')],string='State',default='draft',tracking= True)
    

    @api.depends('commodity_id.volume')
    def _compute_total_volume(self):
        for record in self:
            total_volume = sum(line.volume for line in record.commodity_id)
            record.line_total = total_volume 
  

    def _str_to_time(self, time_str):
        try:
            return datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError:
            return None
        
    @api.model
    def create(self, vals):
        # Create the record
        record = super(DailyArrivalEntry, self).create(vals)

        return record

   
    @api.depends('arrival_date')
    def _compute_nepali_dates(self):
        for record in self:
            if record.arrival_date:
                arrival_nepali_date = nepali_datetime.date.from_datetime_date(record.arrival_date)
                record.arrival_date_bs = arrival_nepali_date.strftime('%Y-%m-%d')
            else:
                record.arrival_date_bs = False
    # @api.constrains('mobile_number')
    # def _check_mobile_length_and_prefix(self):
    #     for record in self:
    #         if record.mobile_number:
    #             if not record.mobile_number.isdigit() or len(record.mobile_number) != 10 or not record.mobile_number.startswith(('97', '98')):
    #                 raise ValidationError("Mobile Number must be 10 digits long and start with 97 or 98.")
    
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
    #             # 'default_parking_duration': self.duration,
    #             # 'default_amount': self.parking_cost,
    #             # 'default_ref': self.final_number,
    #             'active_id': self.id, 
    #         },
    #         'target': 'new',
    #     }


   

    # @api.onchange('commodity_id')
    # def _raise_warning(self): 
    #     if self.line_total > self.volume:
    #         return {
    #             'warning': {
    #                 'title': 'Total Mismatch Warning',
    #                 'message': 'The total of commodity lines does not match the actual total. Please review the totals.'
    #             }
    #         }
    # @api.constrains('line_total', 'total')
    # def _check_total_match(self):
    #     for rec in self:
    #         if rec.line_total != rec.volume:
    #             raise ValidationError(
    #                 _('The total of commodity li nes does not match the actual total. Please review the totals.')
    #             )



    # def _float_to_time(self, float_time):
    #     parts = float_time.split(':')
    #     hours = int(parts[0])
    #     minutes = int(parts[1])
    #     seconds = int(parts[2]) if len(parts) > 2 else 0
    #     return time(hours, minutes, seconds)
    
    # def action_check_in(self):
    #     """Method for checking in"""
    #     self.state = 'check_in'
    #     self.check_in_bool = True
    #     self.check_out_bool = False
    #     current_time = datetime.now(timezone('Asia/Kathmandu'))
    #     self.check_in_time = current_time.strftime('%H:%M:%S')
    #     if not self.parking_cost and self.vehicle_type:
    #         self.parking_cost = self.vehicle_type.cost_per_hour
        
    #     self.env['amp.vehicle.number'].sudo().create({
    #         'number': self.final_number,
    #         'company_id': self.company_id.id,
    #         'date': self.arrival_date
    #     })


    # def action_check_in(self):
    #     """Method for checking in"""
    #     # Ensure the vehicle is not already checked in
    #     existing_vehicle_record = self.env['vehicle.number'].sudo().search([
    #         ('final_number', '=', self.default_vehicle_number.final_number),
    #         ('company_id', '=', self.company_id.id),
    #         ('state', '=', 'check_in'),
    #     ], limit=1)

    #     if existing_vehicle_record:
    #         raise ValidationError(_(
    #             "The vehicle with number '%s' is already checked in. Please ensure it has checked out before checking in again."
    #         ) % self.default_vehicle_number.final_number)

    #     # Proceed with check-in
    #     # existing_vehicle_record.date_bs = self.check_in_date_bs
    #     # print(self.check_in_date_bs)
    #     self.state = 'check_in'
    #     self.check_in_bool = True 
    #     self.check_out_bool = False
    #     current_time = datetime.now(timezone('Asia/Kathmandu'))
    #     self.check_in_time = current_time.strftime('%H:%M:%S')
    #     self.check_in_date = fields.Date.context_today(self)
    #     self.check_in_date_bs = nepali_datetime.date.from_datetime_date(self.check_in_date)
    #     self.arrival_date = fields.Date.context_today(self)
    #     self.arrival_date_bs = nepali_datetime.date.from_datetime_date(self.arrival_date)

    #     # if not self.parking_cost and self.vehicle_type:
    #     #     self.parking_cost = self.vehicle_type.cost_per_hour
        
    #     # Check if the vehicle number exists in the amp.vehicle.number model
    #     # existing_vehicle_number = self.env['amp.vehicle.number'].sudo().search([
    #     #     ('number', '=', self.final_number),
    #     #     ('company_id', '=', self.company_id.id),
    #     # ], limit=1)

    #     if self.vehicle_system == "old":
    #         vehicle_system = "old"
    #     else:
    #         vehicle_system = "new"

        # if not existing_vehicle_number:
            # If no record exists, create a new one
        # self.env['vehicle.number'].sudo().create({
        #     # 'final_number': self.final_number,
        #     'company_id': self.company_id.id,
        #     'check_in_date': self.check_in_date,
        #     'check_in_date_bs': self.check_in_date_bs,
        #     'arrival_date': self.arrival_date,
        #     'arrival_date_bs': self.arrival_date_bs,
        #     'vehicle_system': vehicle_system,
        #     'company_id':self.company_id.id,

        #     'check_in_time': self.check_in_time,
        #     'default_vehicle_number': self.default_vehicle_number.id,

        #     'vehicle_classification':self.vehicle_classification,
        #     # 'vehicle_type':self.vehicle_type.id,
        #     'zonal_id':self.zonal_id.id,
        #     'lot_number':self.lot_number,
        #     'custom_number':self.custom_number,
        #     'zonal_code':self.zonal_code,
        #     'vehicle_number':self.vehicle_number,
            
        #     # 'province':self.province.id,
        #     'heavy':self.heavy,
        #     'two_wheeler':self.two_wheeler,
        #     'four_wheeler':self.four_wheeler,
        #     'province_number':self.province_number,
        #     'province_code':self.province_code,
        #     'vehicle_code':self.vehicle_code,
            
        #     # 'mobile_number':self.mobile_number,
            
        #     'state': 'check_in',
        # })
        # else:
        #     # Update the state to check-in for an existing record
        #     existing_vehicle_number.write({'state': 'check_in'})

    # def action_check_out(self):
    #     """Method for checking out"""
    #     existing_vehicle_number = self.env['vehicle.number'].sudo().search([
    #         ('final_number', '=', self.default_vehicle_number.final_number),
    #         ('company_id', '=', self.company_id.id),
    #     ], limit=1)
    #     self.state = 'check_out'
    #     existing_vehicle_number.state=self.state
    #     self.check_out_bool = True
    #     self.check_in_bool = False
    #     self.check_out_date = fields.Date.context_today(self)
    #     self.check_out_date_bs = nepali_datetime.date.from_datetime_date(self.check_out_date)
    #     # existing_vehicle_number.date_bs = self.check_out_date_bs
    #     current_time = datetime.now(timezone('Asia/Kathmandu'))
        # self.check_out_time = current_time.strftime('%H:%M:%S')  
        # self._compute_duration()
        # existing_vehicle_number.duration = self.duration
        # existing_vehicle_number.hours = self.hours
        # existing_vehicle_number.minutes = self.minutes
        # existing_vehicle_number.seconds = self.seconds

        # if self.vehicle_type and self.vehicle_type.cost_per_hour:
        #     self.parking_cost = self.duration * self.vehicle_type.cost_per_hour




    # @api.constrains('default_vehicle_number', 'arrival_date_bs')
    # def _check_unique_entry(self):
    #     # Check for existing records with the same commodity and date
    #     existing_entry = self.search([
    #         ('default_vehicle_number', '=', self.default_vehicle_number.id),
    #         ('arrival_date_bs', '=', self.arrival_date_bs)
    #     ], limit=1)
        
    #     if existing_entry:
    #         raise ValidationError(f"This commodity{self.default_vehicle_number.final_number} is already have enteries on {self.arrival_date_bs}.")



class TempCommodityAggregation(models.TransientModel):
    _name = 'temp.commodity.aggregation'
    _description = 'Temporary Commodity Aggregation Data'

    name = fields.Char(string="Commodity Name")
    from_volume = fields.Float(string="From Volume")
    to_volume = fields.Float(string="To Volume")
    unit = fields.Char(string="Unit")
    change_rate = fields.Float(string="Change Rate (%)")
    change_types = fields.Char( string="Change Type")



class TempCommodityTime(models.TransientModel):
    _name = 'temp.commodity.arrival.time'
    _description = 'Temporary Commodity Time Data'

    name = fields.Char(string="Commodity Name")
    arrival_date = fields.Char(string="Arrival Date")
    volume = fields.Float(string="Volume")
    unit = fields.Char(string="Unit")


class TempCommodityVehicle(models.TransientModel):
    _name = 'temp.commodity.arrival.vehicle'
    _description = 'Temporary Commodity Time Data'

    final_number = fields.Char(string="Vehicle Number")
    arrival_date = fields.Char(string="Arrival Date")
    check_in_date = fields.Char(string="Check In Date")
    check_out_date = fields.Char(string="Check Out Date")
    duration = fields.Float(string="Duration(Hr)")

class TempCommodity(models.TransientModel):
    _name = 'temp.commodity.arrival'
    _description = 'Temporary Commodity Time Data'

    name = fields.Char(string="Commodity Name")
    arrival_date = fields.Char(string="Arrival Date")
    volume = fields.Float(string="Volume")
    unit = fields.Char(string="Unit")
    
    # @api.model
    # def firstprint(self):
    #     print('Method Called')
    #     context = self.env.context
    #     report_type = context.get('report_type')
    #     date_from = context.get('date_from')
    #     date_to = context.get('date_to')
        
    #     print("Report Type:", report_type)
    #     print("Date From:", date_from)
    #     print("Date To:", date_to)
    #     print("Date To $$$$$$$$$$$$$$$$$$$$$$$$$$:", context.get('from_view'))





    