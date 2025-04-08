
from odoo import fields, models


class ProductTemplateAttributeExclusion(models.Model):
    _name = 'cp.template.attribute.exclusion'
    _description = "Product Template Attribute Exclusion"
    _order = 'product_tmpl_id, id'

    product_template_attribute_value_id = fields.Many2one(
        comodel_name='cp.template.attribute.value',
        string="Attribute Value",
        ondelete='cascade',
        index=True)
    product_tmpl_id = fields.Many2one(
        comodel_name='product.custom.price',
        string="Product Template",
        ondelete='cascade',
        required=True,
        index=True)
    value_ids = fields.Many2many(
        comodel_name='cp.template.attribute.value',
        # relation='product_attr_exclusion_value_ids_rel',
        string="Attribute Values",
        domain="[('product_tmpl_id', '=', product_tmpl_id), ('ptav_active', '=', True)]")
