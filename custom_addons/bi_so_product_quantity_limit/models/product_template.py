# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
	_inherit = "product.template"

	min_qty = fields.Float(string= "Minimum Qty")
	max_qty = fields.Float(string= "Maximum Qty")
	saleable_qty = fields.Float(string= "Saleable Qty")

	@api.constrains('min_qty','max_qty')
	def qty_validate(self):
		for record in self:
			if self.min_qty > self.max_qty:
				raise ValidationError(_("Maximum Qty Should be Greater than Minimum Qty"))
		
	@api.constrains('saleable_qty')
	def saleable_qty_validate(self):
		for record in self:
			if self.saleable_qty > self.qty_available:
				raise ValidationError(_("Saleable Qty Should be Less than Qty on Hand"))