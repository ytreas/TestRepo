from odoo import models,fields,_,api,http
from odoo.http import request
import qrcode
import base64
from io import BytesIO
# from . import constant

class WebsiteWebsite(models.Model):
    _inherit = 'website'

    def get_company_id(self):
        hosturl = request.httprequest.environ['HTTP_REFERER'] if request else 'n/a'
        hosturl = hosturl[hosturl.index('://')+3:]
        hosturl = hosturl[:hosturl.index('/')]
        
        company_detail = http.request.env["res.company.details"].sudo().search([('url', '=', hosturl)])
        
        company = company_detail.parent_id
        
        if company:
            return company
        else:
            return False

    def get_company_name(self):
        try:
            hosturl = request.httprequest.environ['HTTP_REFERER'] if request else 'n/a'
            hosturl = hosturl[hosturl.index('://')+3:]
            hosturl = hosturl[:hosturl.index('/')]
            
            company_detail = http.request.env["res.company.details"].sudo().search([('url', '=', hosturl)])
            
            company = company_detail.parent_id
            
            if company:
                if request.env.context['lang'] == 'ne_NP':
                    return company.name_np
                else:
                    return company.name
            else:
                return False
        except Exception as e:
            return self.company_id.name

    def get_company_type(self):
        try:
            hosturl = request.httprequest.environ['HTTP_REFERER'] if request else 'n/a'
            hosturl = hosturl[hosturl.index('://')+3:]
            hosturl = hosturl[:hosturl.index('/')]
            
            company_detail = http.request.env["res.company.details"].sudo().search([('url', '=', hosturl)])
            
            company = company_detail.parent_id
            
            if company:
                if request.env.context['lang'] == 'ne_NP':
                    return company.palika.type_np + 'पालिका'
                else:
                    return company.palika.type
            else:
                return False
        except Exception as e:
            return self.company_id.name

    def get_company_logo(self):
        try:
            print("HTTP Environ:", request.httprequest.environ)
            
            hosturl = request.httprequest.environ['HTTP_REFERER'] if request else 'n/a'
            hosturl = hosturl[hosturl.index('://')+3:]
            hosturl = hosturl[:hosturl.index('/')]
            
            company_detail = http.request.env["res.company.details"].sudo().search([('url', '=', hosturl)])
            
            company = company_detail.parent_id
            
            if company:
                return company.logo
            else:
                return False
        except Exception as e:
            return self.env.user.company_id.logo

    def get_company_url(self):
        hosturl = request.httprequest.environ['HTTP_REFERER'] if request else 'n/a'
        hosturl = hosturl[hosturl.index('://')+3:]
        hosturl = hosturl[:hosturl.index('/')]
        return hosturl

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _get_report_url(self, record):
        """Generate the preview URL for any record"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/web#id={record.id}&model={record._name}&view_type=form"

    def _get_qr_code(self, record):
        """Generate QR code for any record preview URL"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        url = self._get_report_url(record)
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image()
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_image = base64.b64encode(buffer.getvalue()).decode()
        
        return qr_image