from odoo import api, fields, models, _
import logging
from odoo.exceptions import ValidationError,UserError
_logger = logging.getLogger(__name__)

class Commodity(models.Model):
    _name = 'amp.commodity'
    _rec_name = 'commodity'
    _order = "arrival_date desc" 
    # _inherits = {'product.product': 'product_tmpl_id'}

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    commodity = fields.Many2one(
        comodel_name='product.product',
        string="Commodity",
        required=True
    )
    volume = fields.Float(string="Volume")
    name = fields.Char( string = "Name",related='commodity.name')

    trader_id = fields.Many2one('amp.trader', string='Traders')
    converter = fields.Many2one('uom.uom', string='Convertor')
    total = fields.Float(string='Total', digits=(12, 3), compute='_compute_total', store=True)
    remarks = fields.Text(string='Remarks')
    am_daily_id = fields.Many2one('amp.daily.arrival.entry', string='Daily arrival')
    phone_no = fields.Char(string='Phone No.')
    arrival_date = fields.Date(string='Arrival Date', related='am_daily_id.arrival_date', store=True)
    arrival_date_bs = fields.Char(
        string='Arrival Date (Nepali)', 
        related='am_daily_id.arrival_date_bs', 
        store=True
    )
    check_in_time = fields.Char(string="Check In Time:",related='am_daily_id.check_in_time',store=True)
    check_out_time = fields.Char(string="Check Out Time:",related='am_daily_id.check_out_time',store=True)
    commodity_domain = fields.Char(compute='_compute_commodity_domain', store=False, invisible = True) 
    final_number = fields.Char(
        string="Vehilce Number",
        related = 'am_daily_id.default_vehicle_number.final_number',
        store = True)
    
    unit = fields.Many2one('uom.uom', string="Unit", compute='_compute_unit', store=True)
    # unit = fields.Many2one('uom.uom', string='Unit', required=True, domain="[('id', 'in', unit_domain)]")
    # unit_domain = fields.Many2many('uom.uom', compute='_compute_unit_domain', store=True)

    daily_volume = fields.Float(string="Total Volume (Daily)", compute='_compute_daily_volume', store=False)

    collection_center = fields.Many2one('commodity.center', string="Collection Center")

    trader_domain_ids = fields.Many2many( 
        'amp.trader',
        compute='_compute_trader_domain_ids',
        string='Dynamic Traders Domain'
    )

    # @api.depends('commodity')
    # def _compute_unit_domain(self):
    #     for record in self:
    #         if record.commodity:
    #             # Search for the corresponding commodity master record based on the selected product (commodity)
    #             commodity_master = self.env['amp.commodity.master'].search([('product_id', '=', record.commodity.id)], limit=1)
    #             if commodity_master:
    #                 # Get the unit and other_unit associated with the selected commodity master
    #                 units = [commodity_master.unit.id, commodity_master.other_unit.id] if commodity_master.unit and commodity_master.other_unit else []
    #                 print("Allowed units:", units)
    #                 record.unit_domain = [(6, 0, units)]  # Set the Many2many field with the list of IDs
    #             else:
    #                 record.unit_domain = [(5, 0, 0)]  
    #         else:
    #             record.unit_domain = [(5, 0, 0)]  # Clear the Many2many field if no commodity is selected

    # @api.depends('commodity')
    # def _compute_unit_domain(self):
    #     for record in self:
    #         if record.commodity:
    #             # Get the unit and other_unit associated with the selected commodity
    #             units = [record.commodity.unit.id, record.commodity.other_unit.id] if record.commodity.unit and record.commodity.other_unit else []
    #             print("units", units)
    #             record.unit_domain = [(6, 0, units)]  # Set the Many2many field with the list of IDs
    #         else:
    #             record.unit_domain = [(5, 0, 0)]  # Clear the Many2many field
                
    @api.depends('collection_center') 
    def _compute_trader_domain_ids(self):
        for record in self:
            if record.collection_center:
                # Get traders from the selected collection center
                record.trader_domain_ids = record.collection_center.trader_ids
            else:
                # Return an empty list if no collection center is selected
                record.trader_domain_ids = self.env['amp.trader'].browse([])

    @api.depends('commodity', 'arrival_date')
    def _compute_daily_volume(self):
        for record in self:
            if record.commodity and record.arrival_date:
                total_volume = self.env['amp.commodity'].read_group(
                    domain=[
                        ('commodity', '=', record.commodity.id),
                        ('arrival_date', '=', record.arrival_date)
                    ],
                    fields=['volume', 'unit', 'arrival_date'],
                    groupby=['commodity'],
                )
               
                record.daily_volume = total_volume[0]['volume'] if total_volume else 0.0
                record.unit = total_volume[0]['unit'] if total_volume[0].get('unit') else False
                record.arrival_date = total_volume[0]['arrival_date'] if total_volume[0].get('arrival_date') else False
                print(total_volume[0]['unit'])
            else:
                record.daily_volume = 0.0
                record.unit = False
                record.arrival_date = False

    @api.depends('commodity', 'trader_id') 
    def _compute_unit(self):
        for record in self:
            if record.commodity or record.trader_id:
                # Fetch the relevant commodity master record
                commodity_master = self.env['amp.commodity.master'].search([
                    ('product_id', '=', record.commodity.id)
                    # ('trader_id', '=', record.trader_id.id)
                ], limit=1)
                record.unit = commodity_master.unit if commodity_master else False
            else:
                record.unit = False

    @api.constrains('phone_no')
    def _check_mobile_length_and_prefix(self):
        for record in self:
            if record.phone_no:
                if not record.phone_no.isdigit() or len(record.phone_no) != 10 or not record.phone_no.startswith(('97', '98')):
                    raise ValidationError("Phone Number must be 10 digits long and start with 97 or 98.")
    
    @api.depends('trader_id')
    def _compute_commodity_domain(self):
        for record in self:
            if record.trader_id:
                product_ids = record.trader_id.commodity_id.mapped('product_id.id')
                record.commodity_domain = [('id', 'in', product_ids)]
            else:
                record.commodity_domain = [('id', 'in', [])]

 
    @api.onchange('trader_id')
    def _onchange_trader_id(self):
        for record in self:
            if record.trader_id:
                record.phone_no = record.trader_id.phone
        # if self.trader_id:
        #     print("sahdkasjhdkjashdkjashdjahskjdhaskjdhkasjhdkjasdh")
        #     # Extract product IDs from the One2many field `commodity_id`
        #     product_ids = self.trader_id.commodity_id.mapped('product_id.id')
        #     print("product_ids",product_ids)
        #     return {'domain': {'commodity': [('id', 'in', product_ids)]}}
        # else:
        #     return {'domain': {'commodity': []}}

    @api.onchange('phone_no')
    def _onchange_phone_no(self):
        for record in self:
            if record.trader_id and record.phone_no:
                record.trader_id.phone = record.phone_no

    @api.depends('volume', 'converter','unit') 
    def _compute_total(self):
        for rec in self:
            if rec.converter:
                print("rec.volume", rec.converter.uom_type)
                if rec.volume:     
                    if rec.converter.uom_type == rec.unit.uom_type == "reference":
                        rec.total = float(rec.volume)        
                    if rec.converter.uom_type == 'smaller':
                        rec.total = round(float(rec.volume / rec.converter.ratio), 3)
                    elif rec.converter.uom_type == 'bigger':

                        rec.total = float(rec.volume * rec.converter.ratio)
                    elif rec.converter.uom_type == 'reference':
                        rec.total = float(rec.volume)
                else:
                    rec.total = 0.0
            else:
                rec.total = 0.0

    # @api.model
    # def create(self, vals):
    #     _logger.info(f"Creating amp.commodity with vals: {vals}")
    #     if 'trader_id' not in vals:
    #         raise ValidationError(_('Trader ID must be provided.'))
        
    #     company_product_rule = self.env['ir.rule'].search([('name', '=', 'Company Related Products')], limit=1)
    #     company_product_rule.active = False
        
    #     record = super(Commodity, self).create(vals)
    #     _logger.info(f"Created amp.commodity record: {record}")

    #     if record.trader_id and record.trader_id.company_category:
    #         companies = self.env['res.company'].search([('company_category', '=', record.trader_id.company_category.id)])
    #         for company in companies:
    #             company.write({
    #                 'company_category_product': [(4, record.product_tmpl_id.id)]
    #             })
        
    #     company_product_rule.active = True
    #     return record

    
class CommodityMaster(models.Model):
    _name = 'amp.commodity.master'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product',string="Commodity Name", ondelete='cascade')
    unit = fields.Many2one('uom.uom', string='Standard Unit',required=True)
    other_unit = fields.Many2many('uom.uom', string='Other Unit') 
    # trader_id = fields.Many2one('amp.trader', string='Traders')
    

    @api.model
    def create(self, vals):
        existing_record = self.search([('product_id', '=', vals.get('product_id'))], limit=1)
        if existing_record:
            raise ValidationError("A Commodity with this name already exists.")
        return super(CommodityMaster, self).create(vals)

    # category = fields.Many2one('company.category',string='Company Category',required=True)
    # company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    # @api.model
    # def create(self, vals):
    #     # print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++",self.company_id.id)
    #     if 'commodity_name' in vals:
    #         existing_record = self.search([('commodity_name', '=', vals['commodity_name'])], limit=1)
    #         if existing_record:
    #             raise UserError(_('A commodity with the name "%s" already exists!') % vals['commodity_name'])

    #     record = super(CommodityMaster, self).create(vals)
    #     product_template_vals = {
    #         'name': record.commodity_name,
    #         # 'company_category': record.category.id,
    #         # 'company_id': self.company_id, 
           
    #     }
    #     self.env['product.template'].create(product_template_vals)

    #     return record
    
    # _sql_constraints = [
    #     ('commodity_unique', 'unique(commodity)', 'The commodity must be unique!')
    # ]

class CommodityCenter(models.Model):
    _name = "commodity.center"
    _description = "Commodity Collection Center"

    name = fields.Char(string="Center Name", required=True)
    location = fields.Char(string="Location")
    trader_ids = fields.Many2many("amp.trader", string="Traders")
    status = fields.Selection([
        ("operational", "Operational"),
        ("maintenance", "Under Maintenance"),
        ("closed", "Closed"),
    ], default="operational", string="Status")
