from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import logging
_logger = logging.getLogger(__name__)

class AmpTrader(models.Model):
    _name = 'amp.trader'
    _description = 'AMP Trader'

    name = fields.Char(string='Name', required=True)
    trader_code = fields.Char(string='Trader Code')
    phone = fields.Char(string='Phone', required=True, size =10)
    email = fields.Char(string='Email')
    street = fields.Char(string='Street', required=True)
    city = fields.Char(string='City', required=True)
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country', required=True)
    partner_id = fields.Many2one('res.partner', string='Related Partner', ondelete='cascade')
    
    # company_category = fields.Many2one('company.category',string='Company Category')
    # commodity_id =fields.One2many('amp.commodity.master','trader_id',string='Commodity')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    commodity_id =fields.Many2many('amp.commodity.master',string='Commodity')
    collection_center = fields.Many2one('commodity.center', string="Collection Center")

    trader_tole_name = fields.Char(string="Tole Name:")
    trader_type = fields.Selection([
        ('wholesaler', 'Wholesaler'),
        ('retailer', 'Retailer'),
        ('farmer', 'Farmer'),
        ('other', 'Other'),
    ], string='Trader Type', required=True)
    trader_province = fields.Many2one('location.province',required=True,string="Province")
    trader_district = fields.Many2one('location.district',required=True,string="District",   domain="[('province_name', '=', trader_province)]" )
    trader_palika = fields.Many2one('location.palika', string="Palika", domain="[('district_name', '=', trader_district)]")
    trader_ward = fields.Char(string="Ward No:")
    
    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:
            _logger.info("Country selected: %s", self.country_id.name)
            return {'domain': {'state_id': [('country_id', '=', self.country_id.id)]}}
        _logger.info("No country selected.")
        return {'domain': {'state_id': []}}
    

    @api.constrains('email')
    def _check_email_format(self):
        for record in self:
            if record.email:
                # Regular expression for validating an Email
                email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
                if not re.match(email_regex, record.email): 
                    raise ValidationError("Invalid email format. Please enter a valid email address.")

    @api.constrains('phone')
    def _check_mobile_length_and_prefix(self):
        for record in self:
            if record.phone:
                # Check if mobile number is 10 digits and starts with 97 or 98
                if not record.phone.isdigit() or len(record.phone) != 10 or not record.phone.startswith(('97', '98')):
                    raise ValidationError("Phone number must be 10 digits long and start with 97 or 98.")

    @api.model
    def create(self, vals):
        # Prepare the values for the res.partner record
        partner_vals = {
            'name': vals.get('name'),
            'phone': vals.get('phone'),
            'email': vals.get('email'),
            'street': vals.get('street'),
            'city': vals.get('city'),
            'state_id': vals.get('state_id'),  
            'country_id': vals.get('country_id'),
            'supplier_rank': 1,  # Mark as vendor
        }
        partner = self.env['res.partner'].create(partner_vals)
        
        # Set the partner_id in vals
        vals['partner_id'] = partner.id
 
        # Generate trader_code if not provided
        if 'trader_code' not in vals:
            vals['trader_code'] = self.env['ir.sequence'].next_by_code('amp.trader.code') or '/'

        # Create the amp.trader record
        trader = super(AmpTrader, self).create(vals)
        return trader

    def write(self, vals):
        for trader in self:
            # Update the corresponding res.partner record
            partner_vals = {}
            if 'name' in vals:
                partner_vals['name'] = vals['name']
            if 'phone' in vals:
                partner_vals['phone'] = vals['phone']
            if 'email' in vals:
                partner_vals['email'] = vals['email']
            if 'street' in vals:
                partner_vals['street'] = vals['street']
            if 'city' in vals:
                partner_vals['city'] = vals['city']
            if 'state_id' in vals:
                partner_vals['state_id'] = vals['state_id']
            if 'country_id' in vals:
                partner_vals['country_id'] = vals['country_id']
            
            trader.partner_id.write(partner_vals)
        
        # Update the amp.trader record
        result = super(AmpTrader, self).write(vals)
        return result

    def unlink(self):
        # Unlink the corresponding res.partner record
        partners = self.mapped('partner_id')
        result = super(AmpTrader, self).unlink()
        partners.unlink()
        return result

    # _sql_constraints = [
    #     ('trader_unique', 
    #      'UNIQUE(name, phone, email,trader_code)',
    #      'A trader with the same Name, Phone, Email and Trader Code already exists.') 
    # ]

    @api.constrains('name', 'phone', 'email', 'trader_code')
    def _check_unique_entry(self):
        for record in self:
            existing_phone = self.search([
                ('id', '!=', record.id),
                ('phone', '=', record.phone),
            ], limit=1)

            if existing_phone:
                raise ValidationError(f"A trader with phone {record.phone} already exists.")

            existing_email = self.search([
                ('id', '!=', record.id),
                ('email', '=', record.email),
            ], limit=1)

            if existing_email:
                raise ValidationError(f"A trader with email {record.email} already exists.")

            existing_trader_code = self.search([
                ('id', '!=', record.id),
                ('trader_code', '=', record.trader_code),
            ], limit=1)

            if existing_trader_code:
                raise ValidationError(f"A trader with trader code {record.trader_code} already exists.")
