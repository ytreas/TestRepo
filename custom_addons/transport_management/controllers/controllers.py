# -*- coding: utf-8 -*-
# from odoo import http


# class TransportManagement(http.Controller):
#     @http.route('/transport_management/transport_management', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/transport_management/transport_management/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('transport_management.listing', {
#             'root': '/transport_management/transport_management',
#             'objects': http.request.env['transport_management.transport_management'].search([]),
#         })

#     @http.route('/transport_management/transport_management/objects/<model("transport_management.transport_management"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('transport_management.object', {
#             'object': obj
#         })

