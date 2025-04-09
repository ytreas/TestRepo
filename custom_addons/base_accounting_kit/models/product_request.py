from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ProductRequest(models.Model):
    _name = 'product.request'
    _description = 'Product Request'

    name = fields.Char(string='Product Name', required=True)
    description = fields.Text(string='Description')
    sale_price = fields.Float(string='Sale Price', required=True)
    cost_price = fields.Float(string='Cost Price', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    product_business_type = fields.Many2many(
        "company.category",
        string="Business Type",
        required=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved')
    ], string='Status', default='draft', readonly=True)
    image_image = fields.Binary(string='Image')
    # company_category_ids = fields.Many2many(
    #     "company.category",
    #     string="Business Type",
    #     compute="_compute_company_category_ids",
    #     store=True
    # )

    # def _compute_company_category_ids(self):
    #     for record in self:
    #         company_categories = record.env.user.company_id.company_category.ids
    #         record.company_category_ids = [(6, 0, company_categories if company_categories else [])]

    # @api.model
    # def create(self, vals):
    #     record = super(ProductRequest, self).create(vals)
    #     record._compute_company_category_ids()
    #     return record

    # def write(self, vals):
    #     result = super(ProductRequest, self).write(vals)
    #     self._compute_company_category_ids()
    #     return result

    @api.constrains('sale_price', 'cost_price')
    def _check_prices(self):
        for record in self:
            if record.cost_price > record.sale_price:
                raise ValidationError("Cost Price must be less than or equal to Sale Price.")

    def action_approve(self):
        self.ensure_one()
        if self.state == 'approved':
            raise ValidationError("This request is already approved.")

        # Create product
        product = self.env['product.product'].create({
            'name': self.name,
            'type': 'product',
            'list_price': self.sale_price,
            'standard_price': self.cost_price,
            'description': self.description,
            'image_1920': self.image_image,
        })

        # Create custom price entry
        custom_price_vals = {
            'product_id': product.product_tmpl_id.id,
            'price_sell': self.sale_price,
            'price_cost': self.cost_price,
            'company_id': self.create_uid.company_id.id,
            'product_featured_image': self.image_image,
        }
        self.env['product.custom.price'].create(custom_price_vals)

        # Create a business.based.products record
        business_product = self.env['business.based.products'].create({
            'product_id': product.product_tmpl_id.id,
            'company_id': self.company_id.id,
        })
        
        # Add the product to each business type by updating their products_ids field
        for business_type in self.product_business_type:
            # Update the business_id on the business.based.products record
            business_product.business_id = business_type.id
            
            # Add the product to the business type's products_ids
            business_type.write({
                'products_ids': [(4, business_product.id)]
            })
        self.company_id.sudo()._compute_company_category_product()
        self.write({'state': 'approved'})
        return True
