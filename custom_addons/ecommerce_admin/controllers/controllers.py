# -*- coding: utf-8 -*-
# from odoo import http


# class EcommerceAdmin(http.Controller):
#     @http.route('/ecommerce_admin/ecommerce_admin', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ecommerce_admin/ecommerce_admin/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ecommerce_admin.listing', {
#             'root': '/ecommerce_admin/ecommerce_admin',
#             'objects': http.request.env['ecommerce_admin.ecommerce_admin'].search([]),
#         })

#     @http.route('/ecommerce_admin/ecommerce_admin/objects/<model("ecommerce_admin.ecommerce_admin"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ecommerce_admin.object', {
#             'object': obj
#         })

