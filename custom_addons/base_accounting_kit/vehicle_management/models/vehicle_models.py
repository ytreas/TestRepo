from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo import models, fields

class VehicleBrand(models.Model):
    _name = 'vehicle.brand'
    _description = 'Vehicle Brand'
    _rec_name = 'brand_name'
    _order = 'brand_name asc'

    code = fields.Char(
        string="Code", 
        required=True, 
        unique=True,
        tracking=True,
        help="Unique identifier for the vehicle brand"
    )
    brand_name = fields.Char(
        string="Brand Name", 
        required=True,
        tracking=True,
        help="Name of the vehicle brand"
    )
    brand_name_np = fields.Char(
        string="Brand Name(np)", 
        required=True,
        tracking=True,
        help="Name of the vehicle brand"
    )
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        required=True, 
        default=lambda self: self.env.company
    )
    # model_count = fields.Integer(
    #     string="Number of Models",
    #     compute='_compute_model_count'
    # )
    
    # def _compute_model_count(self):
    #     for record in self:
    #         record.model_count = len(record.vehicle_model_ids)

class VehicleModel(models.Model):
    _name = 'vehicle.model'
    _description = 'Vehicle Model'
    _rec_name = 'model_name'
    _order = 'model_name asc'

    code = fields.Char(
        string="Code", 
        required=True, 
        unique=True,
        tracking=True,
        help="Unique identifier for the vehicle model"
    )
    model_name = fields.Char(
        string="Model Name", 
        required=True,
        tracking=True,
        help="Name of the vehicle model"
    )
    cc = fields.Integer(
        string="Cubic Centimeter (CC)",
        tracking=True,
        help="Engine capacity in cubic centimeters"
    )
    brand_id = fields.Many2one(
        'vehicle.brand', 
        string="Brand", 
        required=True,
        tracking=True,
        ondelete='restrict'
    )
    vehicle_number_id = fields.One2many(
        'vehicle.number', 
        'vehicle_model', 
        string='Vehicle Numbers'
    )
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        required=True, 
        default=lambda self: self.env.company
    )
    engine_number = fields.Char("Engine Number")
    chassis_number = fields.Char("Chassis Number")

    vehicle_count = fields.Integer(
        string="Number of Vehicles",
        compute='_compute_vehicle_count'
    )
    engine_number = fields.Char("Engine Number")
    chassis_number = fields.Char("Chassis Number")
    
    @api.constrains('cc')
    def _check_cc(self):
        for record in self:
            if record.cc and record.cc < 0:
                raise ValidationError(_("CC value cannot be negative"))

    def _compute_vehicle_count(self):
        for record in self:
            record.vehicle_count = len(record.vehicle_number_id)

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            return {'domain': {'model_name': [('brand_id', '=', self.brand_id.id)]}}
        