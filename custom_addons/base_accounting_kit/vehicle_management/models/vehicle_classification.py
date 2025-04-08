from odoo import models, fields ,api

class VehicleNewClassification(models.Model):
    _name = 'vehicle.new.classification'
    _description = 'Vehicle Classification'

    name = fields.Char(string='Vehicle Type', required=True)
    code = fields.Char(string='Classification Code', required=True)
    v_type = fields.Char(string='Vehicle Type', required=True)

class VehicleoldClassification(models.Model):
    _name = 'vehicle.old.classification'
    _description = 'Vehicle Classification'

    code = fields.Char(string='Classification Code', required=True)
    v_type = fields.Char( string='Vehicle Type')
    name = fields.Char(string='Vehicle Category', required=True)

class VehicleZonalCode(models.Model):
    _name = 'vehicle.zonal.classification'
    _description = 'Vehicle Classification'

    code = fields.Char(string='Classification Code', required=True)
    code_np = fields.Char(string='Classification Code', required=True)
    name = fields.Char(string='Zone', required=True)

class Vehicle(models.Model):
    _name = 'custom.vehicle.type'
    _description = 'Vehicle Master Data'
    _rec_name = 'vehicle_type'

    code = fields.Char(string='Vehicle Code', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    name_en = fields.Char(string='Vehicle Name (English)', required=True)
    name_np = fields.Char(string='Vehicle Name (Nepali)', required=True)
    time_duration = fields.Float(string='Time Duration(Hr)', required=True)
    extra_charge = fields.Float(string='Extra Charge(Rs)', required=True)
    cost_per_hour = fields.Float(string='Cost Per Hour(Hr/Rs)', required=True)
    max_weight = fields.Float(string='Max Weight(Kg)', required=True)
    fine_amount = fields.Float(string='Fine Amount(Rs)')
    vehicle_type = fields.Selection([
        ('2_wheeler', '2 Wheeler'),
        ('4_wheeler', '4 Wheeler'),
        ('heavy', 'Heavy Vehicle'),
        ('other', 'Other')
    ], string='Vehicle Type', required=True)

    @api.onchange("name_en","name_np")
    def _onchangeName(self):
        if self.name_en:
            translation_model = self.env['translation.service.mixin']
            self.name_np =  translation_model.translate_to_nepali(self.name_en)
        elif self.name_np:
            translation_model = self.env['translation.service.mixin']
            self.name_en = translation_model.translate_to_english(self.name_np)