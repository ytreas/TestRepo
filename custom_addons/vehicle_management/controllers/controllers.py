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

from odoo import http, fields
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

class VehicleAPI(http.Controller):

    @http.route('/api/update_vlaue', type='json', auth='user', methods=['POST'], csrf=False)
    def update_location(self, **kwargs):
        vehicle_id = kwargs.get('vehicle_id')
        # lat = kwargs.get('latitude')
        # lon = kwargs.get('longitude')
        route_id = kwargs.get('route_id')
        checkpoint_name = kwargs.get('check_point_name')
        space_available = kwargs.get('space_available')
        
        route = request.env['fleet.route'].sudo().browse(route_id)
        if not route:
            return {'status': 'failed', 'message': 'Route not found'}
        else:
            checkpoint = request.env['fleet.route.checkpoint'].sudo().search([
                ('route_id', '=', route.id),
                ('name', '=', checkpoint_name)
            ], limit=1)
            if not checkpoint:
                return {'status': 'error', 'message': 'Checkpoint not found'}

 
            checkpoint.write({
                'space_available': space_available,
                'reached': True,
                'date': fields.Datetime.now()
            })
            return {'status': 'success'}