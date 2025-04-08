from odoo import models, fields, _

class CommodityArrival(models.Model):
    _name = 'commodity.arrival'
    _description = 'Commodity Arrival Information'

    commodity_name = fields.Char(string="Commodity", required=True)
    unit = fields.Char(string="Unit", required=True)
    volume = fields.Float(string="Volume", required=True)
    collection_center = fields.Char(string="Collection Center", required=True)
    trader = fields.Char(string="Trader", required=True)
    trader_phone = fields.Char(string="Trader Phone", required=True)
    arrival_date = fields.Char(string="Arrival Date")
    vehicle_number = fields.Char(string="Vehicle Number")

    def action_export_xlsx(self):
        attachment = self.env['ir.attachment'].search([('name', '=', 'arrivalrecord.xlsx')], limit=1)
        if attachment:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'File not found!',
                    'type': 'danger',
                    'sticky': False,
                }
            }

class Vehicle(models.Model):
    _name = 'vehicle.info'
    _description = 'Vehicle Information'



    vehicle_number = fields.Char(string='Vehicle Number', required=True)
    vehicle_system = fields.Char(string='Vehicle System')
    vehicle_classification = fields.Char(string='Vehicle Classification')
    zone = fields.Char(string='Zone')
    vehicle_type_old = fields.Char(string='Vehicle Type (Old)')
    custom_number = fields.Char(string='Custom Number')
    lot_number_old = fields.Char(string='Lot Number (Old)')
    province_new = fields.Char(string='Province (New)')
    province_number = fields.Char(string='Province Number')
    two_wheeler = fields.Char(string='Two Wheeler')
    four_wheeler = fields.Char(string='Four Wheeler')
    heavy = fields.Char(string='Heavy')

    def action_export_vehicle_xlsx(self):
        attachment = self.env['ir.attachment'].search([('name', '=', 'vehicleinfo.xlsx')], limit=1)
        if attachment:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'File not found!',
                    'type': 'danger',
                    'sticky': False,
                }
            }
