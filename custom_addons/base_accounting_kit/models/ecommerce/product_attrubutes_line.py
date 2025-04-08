
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command


class CustomProductTemplateAttributeLine(models.Model):
    _name = 'cp.template.attribute.line'
    _rec_name = 'attribute_id'
    _rec_names_search = ['attribute_id', 'value_ids']
    _description = "Product Template Attribute Line"
    _order = 'sequence, attribute_id, id'

    active = fields.Boolean(default=True)
    product_tmpl_id = fields.Many2one(
        comodel_name='product.custom.price',
        string="Product Template",
        ondelete='cascade',
        required=True,
        index=True)
    sequence = fields.Integer("Sequence", default=10)
    attribute_id = fields.Many2one(
        comodel_name='cp.attribute',
        string="Attribute",
        ondelete='restrict',
        required=True,
        index=True)
    value_ids = fields.Many2many(
        comodel_name='cp.attribute.value',
        # relation='product_attribute_value_product_template_attribute_line_rel',
        string="Values",
        domain="[('attribute_id', '=', attribute_id)]",
        ondelete='restrict')
    value_count = fields.Integer(compute='_compute_value_count', store=True)
    product_template_value_ids = fields.One2many(
        comodel_name='cp.template.attribute.value',
        inverse_name='attribute_line_id',
        string="Product Attribute Values")

    @api.depends('value_ids')
    def _compute_value_count(self):
        for record in self:
            record.value_count = len(record.value_ids)

    @api.onchange('attribute_id')
    def _onchange_attribute_id(self):
        self.value_ids = self.value_ids.filtered(lambda pav: pav.attribute_id == self.attribute_id)

    @api.constrains('active', 'value_ids', 'attribute_id')
    def _check_valid_values(self):
        for ptal in self:
            if ptal.active and not ptal.value_ids:
                raise ValidationError(_(
                    "The attribute %(attribute)s must have at least one value for the product %(product)s.",
                    attribute=ptal.attribute_id.display_name,
                    product=ptal.product_tmpl_id.display_name,
                ))
            for pav in ptal.value_ids:
                if pav.attribute_id != ptal.attribute_id:
                    raise ValidationError(_(
                        "On the product %(product)s you cannot associate the value %(value)s"
                        " with the attribute %(attribute)s because they do not match.",
                        product=ptal.product_tmpl_id.display_name,
                        value=pav.display_name,
                        attribute=ptal.attribute_id.display_name,
                    ))
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Override to:
        - Activate archived lines having the same configuration (if they exist)
            instead of creating new lines.
        - Set up related values and related variants.

        Reactivating existing lines allows to re-use existing variants when
        possible, keeping their configuration and avoiding duplication.
        """
        create_values = []
        activated_lines = self.env['cp.template.attribute.line']
        for value in vals_list:
            vals = dict(value, active=value.get('active', True))
            # While not ideal for peformance, this search has to be done at each
            # step to exclude the lines that might have been activated at a
            # previous step. Since `vals_list` will likely be a small list in
            # all use cases, this is an acceptable trade-off.
            archived_ptal = self.search([
                ('active', '=', False),
                ('product_tmpl_id', '=', vals.pop('product_tmpl_id', 0)),
                ('attribute_id', '=', vals.pop('attribute_id', 0)),
            ], limit=1)
            if archived_ptal:
                # Write given `vals` in addition of `active` to ensure
                # `value_ids` or other fields passed to `create` are saved too,
                # but change the context to avoid updating the values and the
                # variants until all the expected lines are created/updated.
                archived_ptal.with_context(update_product_template_attribute_values=False).write(vals)
                activated_lines += archived_ptal
            else:
                create_values.append(value)
        res = activated_lines + super().create(create_values)
        if self._context.get("create_product_product", True):
            res._update_product_template_attribute_values()
        res._sync_product_template_attributes()
        return res

    def write(self, values):
        """Override to:
        - Add constraints to prevent doing changes that are not supported such
            as modifying the template or the attribute of existing lines.
        - Clean up related values and related variants when archiving or when
            updating `value_ids`.
        """
        if 'product_tmpl_id' in values:
            for ptal in self:
                if ptal.product_tmpl_id.id != values['product_tmpl_id']:
                    raise UserError(_(
                        "You cannot move the attribute %(attribute)s from the product"
                        " %(product_src)s to the product %(product_dest)s.",
                        attribute=ptal.attribute_id.display_name,
                        product_src=ptal.product_tmpl_id.display_name,
                        product_dest=values['product_tmpl_id'],
                    ))

        if 'attribute_id' in values:
            for ptal in self:
                if ptal.attribute_id.id != values['attribute_id']:
                    raise UserError(_(
                        "On the product %(product)s you cannot transform the attribute"
                        " %(attribute_src)s into the attribute %(attribute_dest)s.",
                        product=ptal.product_tmpl_id.display_name,
                        attribute_src=ptal.attribute_id.display_name,
                        attribute_dest=values['attribute_id'],
                    ))
        # Remove all values while archiving to make sure the line is clean if it
        # is ever activated again.
        if not values.get('active', True):
            values['value_ids'] = [Command.clear()]
        res = super().write(values)
        if 'active' in values:
            self.env.flush_all()
            self.env['product.custom.price'].invalidate_model(['attribute_line_ids'])
        # If coming from `create`, no need to update the values and the variants
        # before all lines are created.
        if self.env.context.get('update_product_template_attribute_values', True):
            self._update_product_template_attribute_values()
        self._sync_product_template_attributes()
        return res

    def unlink(self):
        """Override to:
        - Archive the line if unlink is not possible.
        - Clean up related values and related variants.

        Archiving is typically needed when the line has values that can't be
        deleted because they are referenced elsewhere (on a variant that can't
        be deleted, on a sales order line, ...).
        """
        # Try to remove the values first to remove some potentially blocking
        # references, which typically works:
        # - For single value lines because the values are directly removed from
        #   the variants.
        # - For values that are present on variants that can be deleted.
        self.product_template_value_ids._only_active().unlink()
        # Keep a reference to the related templates before the deletion.
        templates = self.product_tmpl_id
        # Now delete or archive the lines.
        ptal_to_archive = self.env['cp.template.attribute.line']
        for ptal in self:
            try:
                with self.env.cr.savepoint(), tools.mute_logger('odoo.sql_db'):
                    super(CustomProductTemplateAttributeLine, ptal).unlink()
            except Exception:
                # We catch all kind of exceptions to be sure that the operation
                # doesn't fail.
                ptal_to_archive += ptal
        ptal_to_archive.action_archive()  # only calls write if there are records
        # For archived lines `_update_product_template_attribute_values` is
        # implicitly called during the `write` above, but for products that used
        # unlinked lines `_create_variant_ids` has to be called manually.
        # (templates - ptal_to_archive.product_tmpl_id)._create_variant_ids()
        return True

    def _update_product_template_attribute_values(self):
       
        ProductTemplateAttributeValue = self.env['cp.template.attribute.value']
        ptav_to_create = []
        ptav_to_unlink = ProductTemplateAttributeValue
        for ptal in self:
            ptav_to_activate = ProductTemplateAttributeValue
            remaining_pav = ptal.value_ids
            for ptav in ptal.product_template_value_ids:
                if ptav.product_attribute_value_id not in remaining_pav:
                    # Remove values that existed but don't exist anymore, but
                    # ignore those that are already archived because if they are
                    # archived it means they could not be deleted previously.
                    if ptav.ptav_active:
                        ptav_to_unlink += ptav
                else:
                    # Activate corresponding values that are currently archived.
                    remaining_pav -= ptav.product_attribute_value_id
                    if not ptav.ptav_active:
                        ptav_to_activate += ptav

            for pav in remaining_pav:
                # The previous loop searched for archived values that belonged to
                # the current line, but if the line was deleted and another line
                # was recreated for the same attribute, we need to expand the
                # search to those with matching `attribute_id`.
                # While not ideal for peformance, this search has to be done at
                # each step to exclude the values that might have been activated
                # at a previous step. Since `remaining_pav` will likely be a
                # small list in all use cases, this is an acceptable trade-off.
                ptav = ProductTemplateAttributeValue.search([
                    ('ptav_active', '=', False),
                    ('product_tmpl_id', '=', ptal.product_tmpl_id.id),
                    ('attribute_id', '=', ptal.attribute_id.id),
                    ('product_attribute_value_id', '=', pav.id),
                ], limit=1)
                if ptav:
                    ptav.write({'ptav_active': True, 'attribute_line_id': ptal.id})
                    # If the value was marked for deletion, now keep it.
                    ptav_to_unlink -= ptav
                else:
                    # create values that didn't exist yet
                    ptav_to_create.append({
                        'product_attribute_value_id': pav.id,
                        'attribute_line_id': ptal.id,
                        'price_extra': pav.default_extra_price,
                    })
            # Handle active at each step in case a following line might want to
            # re-use a value that was archived at a previous step.
            ptav_to_activate.write({'ptav_active': True})
            ptav_to_unlink.write({'ptav_active': False})
        if ptav_to_unlink:
            ptav_to_unlink.unlink()
        ProductTemplateAttributeValue.create(ptav_to_create)
        self.product_tmpl_id.product_id._create_variant_ids()

    def _without_no_variant_attributes(self):
        return self.filtered(lambda ptal: ptal.attribute_id.create_variant != 'no_variant')

    def action_open_attribute_values(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Product Variant Values"),
            'res_model': 'cp.template.attribute.value',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.product_template_value_ids.ids)],
            'views': [
                (self.env.ref('product.product_template_attribute_value_view_tree').id, 'list'),
                (self.env.ref('product.product_template_attribute_value_view_form').id, 'form'),
            ],
            'context': {
                'search_default_active': 1,
            },
        }

    def _sync_product_template_attributes(self):
        """Sync the product.template model with the attributes and values defined."""
        print("This is the self",self)
        for line in self:
            product_tmpl = line.product_tmpl_id.product_id
            print("This is the product_tmpl",product_tmpl)
            if not product_tmpl:
                continue

            # Find or create the attribute based on its name
            attribute = self.env['product.attribute'].search([
                ('name', '=', line.attribute_id.name)
            ], limit=1)
            if not attribute:
                attribute = self.env['product.attribute'].create({
                    'name': line.attribute_id.name,
                })

            # Find or create attribute values based on their names
            value_ids = []
            for value in line.value_ids:
                print("This is the value",value)
                attr_value = self.env['product.attribute.value'].search([
                    ('name', '=', value.name),
                    ('attribute_id', '=', attribute.id)
                ], limit=1)
                if not attr_value:
                    attr_value = self.env['product.attribute.value'].create({
                        'name': value.name,
                        'attribute_id': attribute.id,
                    })
                value_ids.append(attr_value.id)

            # Check if the attribute exists on the product template
            existing_attribute_line = product_tmpl.attribute_line_ids.filtered(
                lambda l: l.attribute_id.id == attribute.id
            )

            if not existing_attribute_line:
                # If the attribute doesn't exist, create a new line with values
                # print("This is the value",existing_value_ids)
                product_tmpl.write({
                    'attribute_line_ids': [(0, 0, {
                        'attribute_id': attribute.id,
                        'value_ids': [(6, 0, value_ids)],
                    })]
                })
            else:
                # If the attribute exists, update its value_ids
                existing_value_ids = existing_attribute_line.value_ids.mapped('id')
                # print("This is the value",existing_value_ids)
                value_ids_to_add = set(value_ids) - set(existing_value_ids)
                if value_ids_to_add:
                    existing_attribute_line.write({
                        'value_ids': [(4, value_id) for value_id in value_ids_to_add],
                    })
