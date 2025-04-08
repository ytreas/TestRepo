from odoo import models,fields,api,_
from odoo.exceptions import ValidationError
import nepali_datetime

class SaleOrderInherit(models.Model):
    _inherit='sale.order'
    def action_confirm(self):
        res = super(SaleOrderInherit, self).action_confirm()

        for order in self:
            for line in order.order_line:
                product = line.product_id
                company_id = order.company_id.id

                custom_price_record = self.env['product.custom.price'].search([
                    ('product_id', '=', product.product_tmpl_id.id),
                    ('company_id', '=', company_id)
                ], limit=1)

                if custom_price_record:
                    new_qty = custom_price_record.saleable_qty - line.product_uom_qty
                    if new_qty < 0:
                        raise models.ValidationError(
                            f"Not enough saleable quantity for product {product.name} in company {order.company_id.name}."
                        )
                    custom_price_record.with_context(skip_saleable_qty_check=True).write({'saleable_qty': new_qty})

        return res
        
    @api.model
    def get_date_bs(self,date_ad):
        try:
            bs_date = nepali_datetime.date.from_datetime_date(date_ad)
            return bs_date
        except Exception as e:
            raise ValidationError(f'{_("Invalid Date Type provided.")} {e}')

class PickingInherit(models.Model):
    _inherit = "stock.picking"
    
    @api.model
    def get_date_bs(self,date_ad):
        try:
            time =''
            date=date_ad
            if date_ad.time():
                date=date_ad.date()
                time=date_ad.time()
            bs_date = nepali_datetime.date.from_datetime_date(date)
            complete_date_time=f"{bs_date} {time}"
            return complete_date_time
        except Exception as e:
            raise ValidationError(f'{_("Invalid Date Type provided.")} {e}')
    
    
    @api.model
    def get_partner_details(self,partner_id,type):
        vendor_address_np=''
        warehouse_address_np=''
        partner_name_np=''
        owner_name_np=''
        
        partner_user=self.env['res.company'].sudo().search([('partner_id','=',int(partner_id))],limit=1)
        if partner_user:
            vendor_address_np=f"{partner_user.name_np}<br/>{partner_user.street_np} <br/> <span> <i class='fa fa-phone mr-2' aria-hidden='true'></i>{partner_user.mobile or partner_user.phone or ''}</span>"
            warehouse_address_np=f"{partner_user.name_np}<br/>{partner_user.street_np},<br/> <span> <i class='fa fa-phone mr-2' aria-hidden='true'></i>{partner_user.mobile or partner_user.phone or ''}</span>"
            partner_name_np=partner_user.name_np or ''
            owner_name_np=partner_user.owner_name_np or ''
            

        if type=='partner_name':
            return partner_name_np
        
        if type=='vendor_address':
            return vendor_address_np
        if type=='warehouse_address':
            return warehouse_address_np
        if type=='partner_name_np':
            return owner_name_np
        
    @api.model
    def get_product_name_np(self, product_id):
        print("product id",product_id)
        product = self.env['product.template'].sudo().browse(product_id)
        if product.exists():
            product_name_np = product.name_np
            print('product',product_name_np)
            return product_name_np or ''
        return ''
        