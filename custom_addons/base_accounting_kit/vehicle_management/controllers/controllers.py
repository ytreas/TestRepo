# -*- coding: utf-8 -*-
# from odoo import http


# class VehicleManagement(http.Controller):
#     @http.route('/vehicle_management/vehicle_management', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/vehicle_management/vehicle_management/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('vehicle_management.listing', {
#             'root': '/vehicle_management/vehicle_management',
#             'objects': http.request.env['vehicle_management.vehicle_management'].search([]),
#         })

#     @http.route('/vehicle_management/vehicle_management/objects/<model("vehicle_management.vehicle_management"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('vehicle_management.object', {
#             'object': obj
#         })

from odoo import http
from odoo.http import request

class CustomActions(http.Controller):
    @http.route('/custom/route_data', type='http', auth='user')
    def custom_route_data(self):
        # Get the logged-in user's company
        user_company = request.env.user.company_id

        # Redirect to the form view of the user's company
        # The domain for filtering is handled by the controller
        action_url = f'/web#action=vehicle_management.action_data_test&domain=[("id", "=", {user_company.id})]'
        
        # Redirect the user to the correct URL
        return request.redirect(action_url)

