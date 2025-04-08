from odoo import models, fields, api
import nepali_datetime

class VehicleNumber(models.Model):
    _name = 'amp.vehicle.number'
    _description = 'Vehicle Number Data'
    _rec_name = 'number' 

    number = fields.Char(string='Vehicle Number', required=True)
    owner_id = fields.Many2one('custom.vehicle.owner', string='Vehicle Owners')

    #check  in date
    date = fields.Date(string='Latest Entry Date')
    date_bs = fields.Char(string="Latest Entry Date Bs", store=True)

    #arrived date
    arrival_date = fields.Date(string="Arrived Date")
    arrival_date_bs = fields.Char(string="Arrived Date (Nepali)", store = True)

    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company)
    vehicle_system = fields.Char(string='Vehicle System')
    state = fields.Char(string='State')
    hours = fields.Float(string='Hours',store=True)
    minutes = fields.Float(string='Minutes',store=True)
    seconds = fields.Float(string='Seconds',store=True)
    duration = fields.Float(string='Duration', store=True)

    vehicle_classification = fields.Char (string='Vehicle Classification')
    zone = fields.Char(string="Zone")
    zonal_code = fields.Char(string = 'Zonal Code')
    vehicle_number = fields.Char(string='Vehicle Number(code)')
    custom_number = fields.Char(string='Custom Number')
    lot_number = fields.Char(string = 'Lot Number(OLD)',size=2)
    province_number = fields.Char(string='Province Number(NEW)')
    province = fields.Char(string='Province')
    province_code = fields.Char(string = 'Province Code')
    vehicle_code = fields.Char(string='Code')
    mobile_number = fields.Char(string='Mobile Number',size =10)
    vehicle_type = fields.Char(string="Vehicle Type")

    