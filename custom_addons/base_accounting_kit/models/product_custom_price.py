from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError


class ProductCustomPrice(models.Model):
    _inherit = [
        "rating.mixin",
        "website.seo.metadata",
        "website.published.multi.mixin",
        "website.searchable.mixin",
    ]
    _name = "product.custom.price"
    _rec_name="product_name"
    _description = "Custom Prices per Company"

    product_id = fields.Many2one(
        "product.template",
        auto_join=True,
        index=True,
        string="Product",
        required=True,
        ondelete="cascade",
    )
    product_name = fields.Char(compute="_get_product_name")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.user.company_id.id,
        required=True,
        store=True,
        readonly=True,
    )
    price_sell = fields.Float(string="Sell Price", required=True)
    price_cost = fields.Float(string="Cost Price", required=True)

    min_qty = fields.Float(string="Minimum Qty")
    max_qty = fields.Float(string="Maximum Qty")
    saleable_qty = fields.Float(string="Saleable Qty")
    qty_available = fields.Float(
        related="product_id.qty_available", string="Qty on Hand", readonly=True
    )
    virtual_available = fields.Float(
        related="product_id.virtual_available", string="Forecasted Qty", readonly=True
    )
    
    sales_price = fields.Float(related='product_id.list_price', string="Sales Price", readonly=True)
    cost_price = fields.Float(related='product_id.standard_price', string="Cost Price", readonly=True)
    sale_ok = fields.Boolean(string="Can be Sold",default=True)
    purchase_ok = fields.Boolean(string="Can be Purchased",default=True)
    product_featured_image = fields.Binary(
        string="Product Featured Image", required=True, store=True,attachment=True
    )
    product_description = fields.Html("Product description")
    discount = fields.Float("Discount Percentage")

    product_ribbon = fields.Selection(
        [
            ("sale", "Sale (#1)"),
            ("sold_out", "Sold out (#2)"),
            ("out_of_stock", "Out of stock (#3)"),
            ("new", "New!!! (#3)"),
        ]
    )
    product_recommendations = fields.Many2many(
        "product.custom.price",
        "product_recommendations_rel",
        "current_id",
        "related_id",
    )
    
    product_attributes_ids=fields.One2many('cp.template.attribute.line', 'product_tmpl_id', 'Product Attributes', copy=True)
    
    
    ribbon_id = fields.Many2one(string="Variant Ribbon", comodel_name="product.ribbon")
    product_template_image_ids = fields.One2many(
        string="Extra Product Media",
        comodel_name="product.image",
        inverse_name="custom_product_tmpl_id",
        copy=True,
    )
    publish = fields.Boolean(default=False)
    free_delivery = fields.Boolean(default=False)
    image_variant_1920 = fields.Image("Variant Image", max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_variant_1024 = fields.Image(
        "Variant Image 1024",
        related="image_variant_1920",
        max_width=1024,
        max_height=1024,
        store=True,
    )
    image_variant_512 = fields.Image(
        "Variant Image 512",
        related="image_variant_1920",
        max_width=512,
        max_height=512,
        store=True,
    )
    image_variant_256 = fields.Image(
        "Variant Image 256",
        related="image_variant_1920",
        max_width=256,
        max_height=256,
        store=True,
    )
    image_variant_128 = fields.Image(
        "Variant Image 128",
        related="image_variant_1920",
        max_width=128,
        max_height=128,
        store=True,
    )
    can_image_variant_1024_be_zoomed = fields.Boolean(
        "Can Variant Image 1024 be zoomed",
        compute="_compute_can_image_variant_1024_be_zoomed",
        store=True,
    )

    # Computed fields that are used to create a fallback to the template if
    # necessary, it's recommended to display those fields to the user.
    image_1920 = fields.Image(
        "Image", compute="_compute_image_1920", inverse="_set_image_1920"
    )
    image_1024 = fields.Image("Image 1024", compute="_compute_image_1024")
    image_512 = fields.Image("Image 512", compute="_compute_image_512")
    image_256 = fields.Image("Image 256", compute="_compute_image_256")
    image_128 = fields.Image("Image 128", compute="_compute_image_128")
    can_image_1024_be_zoomed = fields.Boolean(
        "Can Image 1024 be zoomed", compute="_compute_can_image_1024_be_zoomed"
    )
    
    variant_quantities = fields.One2many(
        "product.variant.quantity", 
        "custom_price_id", 
        string="Variant Quantities",
        compute="_compute_variant_quantities",
        store=True  # This should be True if you want to store the computed value
    )

    @api.depends("product_id")
    def _compute_variant_quantities(self):
        print("here")
        for record in self:
            print("here2")
            if record.product_id:
                print("here3")
                variants = self.env["product.product"].search(
                    [("product_tmpl_id", "=", record.product_id.id)]
                )
                print("variants=====",variants)
                record.variant_quantities = [(0, 0, {
                    "variant_id": variant.id,
                    "variant_name": variant.display_name,
                    "qty_available": variant.qty_available,
                }) for variant in variants]
            else:
                record.variant_quantities = []
    
    def action_update_variant_quantities(self):
        """Method triggered by the 'Update' button."""
        self._compute_variant_quantities()

    @api.depends("image_variant_1920", "image_variant_1024")
    def _compute_can_image_variant_1024_be_zoomed(self):
        for record in self:
            record.can_image_variant_1024_be_zoomed = (
                record.image_variant_1920
                and tools.is_image_size_above(
                    record.image_variant_1920, record.image_variant_1024
                )
            )

    def _compute_image_1920(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_1920 = (
                record.image_variant_1920 or record.product_id.image_1920
            )

    def _compute_image_1024(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_1024 = (
                record.image_variant_1024 or record.product_id.image_1024
            )

    def _compute_image_512(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_512 = record.image_variant_512 or record.product_id.image_512

    def _compute_image_256(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_256 = record.image_variant_256 or record.product_id.image_256

    def _compute_image_128(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_128 = record.image_variant_128 or record.product_id.image_128

    def _compute_can_image_1024_be_zoomed(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.can_image_1024_be_zoomed = (
                record.can_image_variant_1024_be_zoomed
                if record.image_variant_1920
                else record.product_id.can_image_1024_be_zoomed
            )

    def _get_placeholder_filename(self, field):
        image_fields = ["image_%s" % size for size in [1920, 1024, 512, 256, 128]]
        if field in image_fields:
            return "product/static/img/placeholder_thumbnail.png"
        return super()._get_placeholder_filename(field)

    def _get_images(self):
        # self.ensure_one()
        variant_images = list(self.product_template_image_ids)
        if self.image_variant_1920:
            variant_images = [self] + variant_images
        else:
            variant_images = variant_images + [self]
        return variant_images
 
        
    @api.constrains("min_qty", "max_qty")
    def qty_validate(self):
        if self.min_qty > self.max_qty:
            raise ValidationError(_("Maximum Qty Should be Greater than Minimum Qty"))

    @api.depends("product_id")
    def _get_product_name(self):
        for rec in self:
            rec.product_name = rec.product_id.name

    @api.constrains("saleable_qty")
    def saleable_qty_validate(self):
        print("saleable_qty", self.saleable_qty)
        print("qty_available", self.product_id.qty_available)
        if self.saleable_qty > self.product_id.qty_available:
            raise ValidationError(_("Saleable Qty Should be Less than Qty on Hand"))

    @api.constrains("product_id", "company_id")
    def _check_unique_company_product(self):
        for record in self:
            domain = [
                ("company_id", "=", record.company_id.id),
                ("product_id", "=", record.product_id.id),
            ]
            existing_records = self.search_count(domain)
            if existing_records > 1:
                raise ValidationError(
                    "Only one price record per product can exist for each company."
                )

    @api.model
    def create(self, vals):
        # Assign company_id if it is not in vals
        if "company_id" not in vals:
            vals["company_id"] = self.env.user.company_id.id
        # Ensure that non-admin users only set prices for their own company
        print("Entering If")
        print(vals["company_id"])
        print(self.env.user.company_id.id)
        print(self.env.user.has_group("base.group_system"))
        if (
            not (str(vals["company_id"]) == str(self.env.user.company_id.id))
        ):
            if not self.env.user.has_group("base.group_system"):
                raise ValidationError("You can only set prices for your own company.")

        return super(ProductCustomPrice, self).create(vals)

    def write(self, vals):
        # Debugging prints (remove/comment in production)
        print("Record's existing company_id:", self.company_id.id)
        print("Is user an admin:", self.env.user.has_group('base.group_system'))
        print("User's company_id:", self.env.user.company_id.id)

        # If the user is not an admin and trying to modify a record outside their company
        if self.env.context.get('skip_saleable_qty_check'):
            pass
        if self.env.context.get('from_button_confirm'):
            pass
        else:
            if str(self.company_id.id) != str(self.env.user.company_id.id):
                if not self.env.user.has_group("base.group_system"):
                    raise ValidationError("You can only set prices for your own company.")
        return super(ProductCustomPrice, self).write(vals)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    custom_price_ids = fields.One2many(
        "product.custom.price", "product_id", string="Custom Prices", readonly=True
    )


class CustomProductTemplateImage(models.Model):
    _inherit = "product.image"

    custom_product_tmpl_id = fields.Many2one(
        "product.custom.price",
        "Custom Product Template",
        index=True,
        ondelete="cascade",
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_custom_price(self, partner_id):
        ref_company_ids = partner_id.ref_company_ids.ids if partner_id else []

        rule = self.env.ref('base_accounting_kit.product_custom_price_company_rule').sudo()
        original_domain = rule.domain_force

        rule.domain_force = "[(1, '=', 1)]"

        try:
            custom_price = self.product_tmpl_id.custom_price_ids.filtered(
                lambda p: p.company_id.id in ref_company_ids
            )
        finally:
            rule.domain_force = original_domain

        return custom_price.price_cost if custom_price else self.standard_price

    def get_custom_saleable_quantity(self, partner_id):
        ref_company_ids = partner_id.ref_company_ids.ids if partner_id else []
        
        rule = self.env.ref('base_accounting_kit.product_custom_price_company_rule').sudo()
        original_domain = rule.domain_force

        rule.domain_force = "[(1, '=', 1)]"

        try:
            custom_price = self.product_tmpl_id.custom_price_ids.filtered(
                lambda p: p.company_id.id in ref_company_ids
            )
        finally:
            rule.domain_force = original_domain

        return custom_price.saleable_qty if custom_price else 0
    
    def deduct_saleable_quantity(self, partner_id, qty):
        ref_company_ids = partner_id.ref_company_ids.ids if partner_id else []
        
        rule = self.env.ref('base_accounting_kit.product_custom_price_company_rule').sudo()
        original_domain = rule.domain_force

        rule.domain_force = "[(1, '=', 1)]"

        try:
            custom_price = self.product_tmpl_id.custom_price_ids.filtered(
                lambda p: p.company_id.id in ref_company_ids
            )
        finally:
            print("here hrereee")
            if custom_price.saleable_qty > 0:
                custom_price.saleable_qty -= qty
            rule.domain_force = original_domain




    
    # def get_custom_cost_price(self, partner_id):
    #     print("Partner ID:", partner_id)
    #     custom_price = self.product_tmpl_id.custom_price_ids.filtered(
    #         lambda p: p.company_id == self.env.user.company_id
    #     )
    #     print("Filtered custom price:", custom_price)
        
    #     return custom_price.price_cost if custom_price else self.standard_price
    
# class SaleOrderLine(models.Model):
#     _inherit = 'sale.order.line'

    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     if self.product_id:
    #         if self.partner_id:
    #             custom_price = self.product_id.get_custom_price(self.partner_id)
    #             self.price_unit = custom_price


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id and self.partner_id:
            print("Partner ID:", self.partner_id.id)
            custom_price = self.product_id.get_custom_price(self.partner_id)
            print("Custom price for partner:", custom_price)
            self.price_unit = custom_price

    @api.constrains('product_qty')
    def _check_saleable_qty(self):
        for line in self:
            saleable_quantity=line.product_id.get_custom_saleable_quantity(self.partner_id)
            print("saleable_quantity",saleable_quantity)
            if saleable_quantity:
                if self.product_qty > saleable_quantity:
                    raise ValidationError(
                        _(  f"You cannot purchase {line.product_id.name} because only {saleable_quantity} are available for sale.")
                    )
                    
class ProductVariantQuantity(models.Model):
    _name = "product.variant.quantity"
    _description = "Product Variant Quantity"

    custom_price_id = fields.Many2one(
        "product.custom.price",
        string="Custom Price",
        ondelete="cascade",
    )
    variant_id = fields.Many2one(
        "product.product",
        string="Variant",
        required=True,
        ondelete="cascade",
    )
    variant_name = fields.Char(related="variant_id.display_name", string="Variant Name")
    qty_available = fields.Float(
        related="variant_id.qty_available", string="Qty on Hand", readonly=True
    )

    