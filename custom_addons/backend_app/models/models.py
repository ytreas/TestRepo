# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class app_backend(models.Model):
#     _name = 'app_backend.app_backend'
#     _description = 'app_backend.app_backend'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

