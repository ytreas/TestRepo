from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import uuid
from datetime import date
from odoo.http import request

class SaleDate(models.Model):
    _inherit = "sale.order"
    
    validity_date = fields.Date(string= "Expiration Date")
    validity_date_bs = fields.Char(string= "Expiration Date BS")
    
 
    # date_order_bs = fields.Char(string= "Quotation Date BS",visible=1)
    
class PurchaseDate(models.Model):
    _inherit = "purchase.order"
    
    date_planned = fields.Date(string= "Expected Arrival ")
    date_planned_bs = fields.Char(string= "Expected Arrival BS")

class PurchaseDate(models.Model):
    _inherit = "account.move"
    
    invoice_date= fields.Date(string= "Due Date ")
    invoice_date_bs = fields.Char(string= "Due Date BS")
    
    @api.onchange('date')
    def check(self):
        print("================",self.date_bs)
        print("=====+++++++++++",self.date)


