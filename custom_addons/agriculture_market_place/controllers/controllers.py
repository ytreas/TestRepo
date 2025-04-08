# from odoo import http
# from odoo.http import request
# from werkzeug.urls import url_decode 
# from datetime import datetime
# import json

# class ReportController(http.Controller):
#     @http.route('/report/view_daily_price_report', type='http', auth='public')
#     def view_daily_price_report(self, **kwargs):
#         print("we are here")
#         # Extract the report_data from the kwargs
#         report_data = request.params.get('report_data')
#         print("_++++++++++++++++++++++++++++++++++++",report_data)
#         # if not report_data:
#         #     return http.Response("No report data provided", status=400)

#         # # Load the JSON data directly
#         try:
#             context = json.loads(report_data)
#         except json.JSONDecodeError:
#             return http.Response("Invalid report data format", status=400)

#         daily_price_report = context.get('daily_price_report', [])

#         # Render the template
#         return request.render('agriculture_market_place.preview_daily_price_report', {
#             'daily_price_report': daily_price_report,
#         })

from odoo import http
from odoo.http import request, content_disposition
from io import BytesIO
import logging
import base64


_logger = logging.getLogger(__name__)

class CustomReportController(http.Controller):
    
    @http.route('/report/pdf', type='http', auth='public', methods=['GET'], csrf=False)
    def generate_report(self, **kwargs):
        _logger.info("we are here ****************************")
        

        report_type = kwargs.get('report_type', None)
        date_from = kwargs.get('date_from', None)
        date_to = kwargs.get('date_to', None)
        commodity = kwargs.get('commodity', None)
        date = kwargs.get('date', None)
        
        records = request.env['temp.commodity.arrival'].search([])


        for record in records:
            _logger.info("Fetched record ID: %s", record.id)
        
        if not records:
            raise ValueError("No records found for the report.")


        report_data = {
            'records': records,
            'report_type': report_type,
            'date_from': date_from,
            'date_to': date_to,
            'date': date,
            'commodity': commodity,
        }

        report_action = request.env.ref('agriculture_market_place.action_report_template_one')
        print("report_action",report_action)
        
        if not report_action:
            raise ValueError("Report template not found")

        pdf_data, _ = request.env['ir.actions.report']._render_qweb_pdf('agriculture_market_place.action_report_template_one', [record.id for record in records],report_data)
        pdf_file = BytesIO(pdf_data)
        pdf_file.seek(0)

        return request.make_response(
            pdf_file.read(),
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'attachment; filename="report.pdf"')
            ]
        )
