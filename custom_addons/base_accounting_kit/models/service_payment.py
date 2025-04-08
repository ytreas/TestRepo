from odoo import models, fields, _,api
import uuid
from odoo.exceptions import ValidationError
import nepali_datetime
class ServicePayment(models.Model):
    _name = "lekhaplus.service.payment"

    transaction_id = fields.Char("Transaction ID")
    client = fields.Char("Client")
    service_type = fields.Many2many("company.category", string="Service Types")
    amount = fields.Float("Amount")
    payment_status = fields.Boolean("Payment Status", default=False)
    valid_until = fields.Date("Valid Until")
    subscription_status = fields.Boolean("Subscription Status", default=False)
    payment_date = fields.Date("Payment Date", default=fields.Date.today)
    payment_provider_status = fields.Boolean("Payment Provider Status", default=False)
    promo_code = fields.Char("Promo Code")
    remarks = fields.Char("Remarks")
    
    
class AccountPaymentInherit(models.Model):
    _inherit="account.payment"
    
    @api.model
    def get_date_bs(self,date):
        try:
            bs_date = nepali_datetime.date.from_datetime_date(date)
            return bs_date
           
        except Exception as e:
            raise ValidationError(_("Invalid Date Type provided."))
