from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
import nepali_datetime
from odoo.exceptions import UserError
import xlsxwriter
import io
import base64

class DailyPrice(models.Model):
    _name = 'amp.daily.price'
    

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    max_price = fields.Float(string='Maximum Price')
    min_price = fields.Float(string='Minimum Price')
    avg_price = fields.Float(string='Average Price')
    commodity = fields.Many2one(comodel_name='amp.commodity.master', string='Commodity')
    unit = fields.Many2one('uom.uom', string='Unit',related = "commodity.unit", store=True)
    unit_import = fields.Char( string=' Unit')
    commodity_name = fields.Char(string='Commodity Name')



    price1 = fields.Float(string='Price 1')
    price2 = fields.Float(string='Price 2')
    price3 = fields.Float(string='Price 3')
    price4 = fields.Float(string='Price 4')
    price5 = fields.Float(string='Price 5')
    trader1 = fields.Many2one('amp.trader', 'Trader 1')
    trader2 = fields.Many2one('amp.trader', 'Trader 2')
    trader3 = fields.Many2one('amp.trader', 'Trader 3')
    trader4 = fields.Many2one('amp.trader', 'Trader 4')
    trader5 = fields.Many2one('amp.trader', 'Trader 5')
    
    current_date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    current_date_bs = fields.Char(string="Current Date (BS)", compute="_compute_current_date_bs",store=True)
    
    last_max = fields.Float(string="Last Recorded Maximum Price")
    last_min = fields.Float(string="Last Recorded Minimum Price")
    last_avg = fields.Float(string="Last Recorded Average Price")

    serial_number = fields.Integer(string="Serial Number")
    
    trader1_domain_ids = fields.Many2many(
        'amp.trader',
        compute='_compute_trader1_domain_ids',
        string='Dynamic Domain for Trader 1'
    )
    trader2_domain_ids = fields.Many2many(
        'amp.trader',
        compute='_compute_trader2_domain_ids',
        string='Dynamic Domain for Trader 2'
    )
    trader3_domain_ids = fields.Many2many(
        'amp.trader',
        compute='_compute_trader3_domain_ids',
        string='Dynamic Domain for Trader 3'
    )
    trader4_domain_ids = fields.Many2many(
        'amp.trader',
        compute='_compute_trader4_domain_ids',
        string='Dynamic Domain for Trader 4'
    )
    trader5_domain_ids = fields.Many2many(
        'amp.trader',
        compute='_compute_trader5_domain_ids',
        string='Dynamic Domain for Trader 5'
    )

    @api.depends('trader2', 'trader3', 'trader4', 'trader5')
    def _compute_trader1_domain_ids(self):
        for record in self:
            # Exclude traders selected in other fields
            excluded_traders = record.trader2 + record.trader3 + record.trader4 + record.trader5
            record.trader1_domain_ids = self.env['amp.trader'].search([('id', 'not in', excluded_traders.ids)])

    @api.depends('trader1', 'trader3', 'trader4', 'trader5')
    def _compute_trader2_domain_ids(self):
        for record in self:
            # Exclude traders selected in other fields
            excluded_traders = record.trader1 + record.trader3 + record.trader4 + record.trader5
            record.trader2_domain_ids = self.env['amp.trader'].search([('id', 'not in', excluded_traders.ids)])

    @api.depends('trader1', 'trader2', 'trader4', 'trader5')
    def _compute_trader3_domain_ids(self):
        for record in self:
            # Exclude traders selected in other fields
            excluded_traders = record.trader1 + record.trader2 + record.trader4 + record.trader5
            record.trader3_domain_ids = self.env['amp.trader'].search([('id', 'not in', excluded_traders.ids)])

    @api.depends('trader1', 'trader2', 'trader3', 'trader5')
    def _compute_trader4_domain_ids(self):
        for record in self:
            # Exclude traders selected in other fields
            excluded_traders = record.trader1 + record.trader2 + record.trader3 + record.trader5
            record.trader4_domain_ids = self.env['amp.trader'].search([('id', 'not in', excluded_traders.ids)])

    @api.depends('trader1', 'trader2', 'trader3', 'trader4')
    def _compute_trader5_domain_ids(self):
        for record in self:
            # Exclude traders selected in other fields
            excluded_traders = record.trader1 + record.trader2 + record.trader3 + record.trader4
            record.trader5_domain_ids = self.env['amp.trader'].search([('id', 'not in', excluded_traders.ids)])

    @api.depends('current_date')
    def _compute_current_date_bs(self):
        for record in self:
            if record.current_date:
                nepali_date = nepali_datetime.date.from_datetime_date(record.current_date)
                record.current_date_bs = nepali_date.strftime('%Y-%m-%d')
            else:
                record.current_date_bs = False

    @api.onchange('unit')
    def _onchange_unit(self):
        if self.unit:
            self.price1 = 0.0  # Reset price1 when unit changes
            unit_name = self.unit.name or ''
            self.price1_label = f'Price per {unit_name}'  # Update the label
        else:
            self.price1_label = 'Price'  # Default label if no unit selected

    price1_label = fields.Char(string='Enter Prices', compute='_compute_price_label')

    @api.onchange('commodity')
    def _onchange_commodity(self):
        if self.commodity:
            self.commodity_name = self.commodity.product_id.name
        else:
            self.commodity_name = False
    @api.depends('unit')
    def _compute_price_label(self):
        for record in self:
            if record.unit:
                record.price1_label = f'Price per {record.unit.name}'
            else:
                record.price1_label = 'Price'
                
    @api.model
    def create(self, vals):
        if not vals.get('min_price') or not vals.get('max_price') or not vals.get('avg_price'):
          
            vals = self._compute_prices(vals)
        daily_price_record = super(DailyPrice, self).create(vals)
        self._create_commodity_master(daily_price_record)

        return daily_price_record

  

    def _create_commodity_master(self, daily_price_record):
        if daily_price_record.unit:
            unit = self.env['uom.uom'].search([('name', '=', daily_price_record.unit.name)], limit=1)
        else:
            unit = self.env['uom.uom'].search([('name', '=', daily_price_record.unit_import)], limit=1)
        if not unit:
            raise ValidationError(f"Unit '{daily_price_record.unit_import}' not found.")
        if daily_price_record.commodity:
            existing_commodity = self.env['product.product'].search([
                ('name', '=',daily_price_record.commodity.product_id.name)
            ], limit=1)  
        else:
            existing_commodity = self.env['product.product'].search([
                ('name', '=',daily_price_record.commodity_name)
            ], limit=1)

        if existing_commodity:
            existing_commodity_master =  self.env['amp.commodity.master'].search([
                ('product_id', '=',existing_commodity.id)], limit=1)
            if existing_commodity_master:
                price_values = {
                    'commodity': existing_commodity_master.id,
                }
                daily_price_record.write(price_values)
            else:
                commodity_values = {
                    'product_id': existing_commodity.id,  
                    'unit': unit.id, 
                }

                success =  self.env['amp.commodity.master'].create(commodity_values)
                if success:
                    price_values = {
                        'commodity': success.id,
                    }
                    daily_price_record.write(price_values)
                else:
                    raise ValidationError("Failed to create/import commodity master. Please check the values.")
        #    raise ValidationError(f"Commodity creation failed. A commodity with name '{daily_price_record.commodity_name}' already exists.")
        else:
            product_values = {
                'name': daily_price_record.commodity_name,  
                'uom_id': unit.id, 
                'uom_po_id':unit.id,
            }
            result = self.env['product.product'].create(product_values)
            if result:
                commodity_values = {
                    'product_id': result.id,  
                    'unit': unit.id, 
                }

                success =  self.env['amp.commodity.master'].create(commodity_values)
                if success:
                    price_values = {
                        'commodity': success.id,
                    }
                    daily_price_record.write(price_values)
                else:
                    raise ValueError("Product creation failed. Please check the Commodity values.")
            else:
                raise ValidationError("Commodity creation/Import failed. Please check the Commodity values.")

    def _compute_prices(self, vals):
        prices = [vals['price1'], vals['price2'], vals['price3'], vals['price4'], vals['price5']]
        filtered_prices = [price for price in prices if price != 0]
        
        if not filtered_prices:
            raise ValidationError(_("At least one price must be entered."))
        
        if len(filtered_prices) != len(set(filtered_prices)):
            raise ValidationError(_("Prices must not be equal."))
        
        vals['min_price'] = min(filtered_prices)
        vals['max_price'] = max(filtered_prices)
        vals['avg_price'] = round(sum(filtered_prices) / len(filtered_prices))
        
        # commodity = self.env['amp.commodity'].browse(vals['commodity'])
        # commodity.product.list_price = vals['avg_price']
        return vals
    
    @api.onchange('commodity')
    def _compute_yesterday_prices(self):
        if self.commodity:
            last_record_of_commodity = self.search([('commodity', '=', self.commodity.id)], order='create_date desc', limit=1)
            self.last_max = last_record_of_commodity.max_price
            self.last_min = last_record_of_commodity.min_price
            self.last_avg = last_record_of_commodity.avg_price
    
    @api.onchange('price1', 'price2', 'price3', 'price4', 'price5')
    def _check_prices_warnings(self):
        prices = [self.price1, self.price2, self.price3, self.price4, self.price5]
        filtered_prices = [price for price in prices if price != 0]

        # Check for abnormal price ranges
        if filtered_prices and max(filtered_prices) > 1.5 * sum(filtered_prices) / len(filtered_prices):
            return {
                'warning': {
                    'title': _("Abnormal Price Detected"),
                    'message': _("One or more prices are significantly different from the rest. Please check the values."),
                }
            }

        # Check for significant increase or decrease in average price
        if filtered_prices:
            current_avg = sum(filtered_prices) / len(filtered_prices)
            
            # Check for increase of more than 50%
            if self.last_avg and current_avg > 1.5 * self.last_avg:
                return {
                    'warning': {
                        'title': _("Significant Increase in Average Price"),
                        'message': _("The current average price has increased by more than 50% compared to the last recorded average. Please verify."),
                    }
                }

            # Check for decrease of more than 50%
            elif self.last_avg and current_avg < 0.5 * self.last_avg:
                return {
                    'warning': {
                        'title': _("Significant Decrease in Average Price"),
                        'message': _("The current average price has decreased by more than 50% compared to the last recorded average. Please verify."),
                    }
                }


    @api.constrains('price1', 'price2', 'price3', 'price4', 'price5')
    def _check_prices(self):
        for record in self:
            prices = [record.price1, record.price2, record.price3, record.price4, record.price5]
            prices = [p for p in prices if p]
            if not prices:
                raise ValidationError(_("At least one price must be entered."))

            if len(prices) != len(set(prices)):
                raise ValidationError(_("Prices must not be equal."))

            record.min_price = min(prices)
            record.max_price = max(prices)
            record.avg_price = sum(prices) / len(prices)

            if len(prices) == 1:
                record.min_price = record.max_price = record.avg_price = prices[0]


    _sql_constraints = [
        ('daily_entry_unique', 
         'UNIQUE(commodity, current_date)', 
         'A record with the same Commodity Name on same date is already enter.')
    ]

    @api.constrains('commodity', 'current_date', 'commodity_name')
    def _check_unique_entry(self):
        for record in self:
            if record.commodity:
                existing_entry = self.search([
                    ('id', '!=', record.id),
                    ('commodity', '=', record.commodity.id),
                    ('current_date', '=', record.current_date)
                ], limit=1)
            else:
                existing_entry = self.search([
                    ('id', '!=', record.id),
                    ('commodity.product_id.name', '=', record.commodity_name),
                    ('current_date', '=', record.current_date)
                ], limit=1)
            if existing_entry:
                name = record.commodity.product_id.name if record.commodity and record.commodity.product_id else record.commodity_name
                raise ValidationError(f"This commodity {name} already has entries on {record.current_date}.")

class TempCommodityPrice(models.TransientModel):
    _name = 'temp.commodity.price'
    _description = 'Temporary Commodity Price Data'

    name = fields.Char(string="Commodity Name")
    unit = fields.Char(string="Unit")
    arrival_date = fields.Char(string="Arrival Date")
    maximum = fields.Float(string="Maximum Price")
    minimum = fields.Float(string="Minimum Price")
    avg_price = fields.Float(string="Average Price")


class TempCommodityPriceNormal(models.TransientModel):
    _name = 'temp.commodity.normal'
    _description = 'Temporary Commodity Price Normal Data'

    name = fields.Char(string="Commodity Name")
    unit = fields.Char(string="Unit")
    arrival_date = fields.Char(string="Arrival Date")
    maximum = fields.Float(string="Maximum Price")
    minimum = fields.Float(string="Minimum Price")
    avg_price = fields.Float(string="Average Price")





class TempCommodityCompare(models.TransientModel):
    _name = 'temp.commodity.compare'

    # Your fields definition, like name, unit, etc.
    name = fields.Char('Commodity Name')
    unit = fields.Char('Unit')
    # arrival_date = fields.Date('Arrival Date')
    # maximum_from = fields.Float('Maximum Price (From Date)')
    # minimum_from = fields.Float('Minimum Price (From Date)')
    avg_price_from = fields.Float('Average Price (From Date)')
    # maximum_to = fields.Float('Maximum Price (To Date)')
    # minimum_to = fields.Float('Minimum Price (To Date)')
    avg_price_to = fields.Float('Average Price (To Date)')

    date_from = fields.Date('From Date')
    date_to = fields.Date('To Date')
    change_rate_avg_price = fields.Float('Change Rate Avg Price (%)')
    change_rate_avg_price_status = fields.Char('Change Status')


    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
        print("Flow is in here")
        res = super(TempCommodityCompare, self).fields_view_get(view_id, view_type, toolbar, submenu)

        # Get the selected dates from the context
        date_from = self._context.get('date_from')
        date_to = self._context.get('date_to')
   

        if date_from and date_to:
            # Extract the date as string
            date_from_str = fields.Date.to_string(date_from)
            date_to_str = fields.Date.to_string(date_to)

            # Modify headers dynamically based on dates
            doc = etree.XML(res['arch'])

            # Set dynamic headers for 'from' and 'to' data
            # for field in doc.xpath("//field[@name='maximum_from']"):
            #     field.set('string', f'Maximum Price ({date_from_str})')

            # for field in doc.xpath("//field[@name='minimum_from']"):
            #     field.set('string', f'Minimum Price ({date_from_str})')

            for field in doc.xpath("//field[@name='avg_price_from']"):
                field.set('string', f'Average Price ({date_from_str})')

            # for field in doc.xpath("//field[@name='maximum_to']"):
            #     field.set('string', f'Maximum Price ({date_to_str})')

            # for field in doc.xpath("//field[@name='minimum_to']"):
            #     field.set('string', f'Minimum Price ({date_to_str})')

            for field in doc.xpath("//field[@name='avg_price_to']"):
                field.set('string', f'Average Price ({date_to_str})')

            res['arch'] = etree.tostring(doc)

        return res
