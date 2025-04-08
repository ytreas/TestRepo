from odoo.fields import Date
from odoo import api,models
from odoo.tools import format_date
# import nepali_datetime


class QwebDateField(models.AbstractModel):
    _inherit = 'ir.qweb.field.date'

    @api.model
    def value_to_html(self, value, options):
        # res = super().value_to_html(value, options)
        # try:       
        #     return nepali_datetime.date.from_datetime_date(value.date())
        # except:
        #     # return nepali_datetime.date.from_datetime_date(value)
        #     try:
        #         return nepali_datetime.date.from_datetime_date(value)
        #     except:
        return value

class QwebDateTimeField(models.AbstractModel):
    _inherit = 'ir.qweb.field.datetime'

    @api.model
    def value_to_html(self, value, options):
        # res = super().value_to_html(value, options)
        # try:       
        #     return str(nepali_datetime.date.from_datetime_date(value.date()))+' '+str(value).split(" ")[1].split('.')[0]
        # except:
        #     try:
        #         return nepali_datetime.datetime.from_datetime_date(value)
        #     except:
        return value