from odoo.http import request
from odoo import http
from odoo import http,api,SUPERUSER_ID
import json
import jwt
from odoo.addons.web.controllers.export import ExcelExport

class AccountingController(ExcelExport):
    @http.route('/export_report', type='http',website=True, auth="public",methods=['GET'])
    def export_report(self, **kw):
        data = kw.get('data')
        export_data = jwt.decode(data,'secret',algorithms="HS256")
        print("export_data",export_data)
        return self.index(json.dumps(export_data.get('data')))