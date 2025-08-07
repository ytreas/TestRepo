from odoo import http
from odoo.http import request
from base64 import b64encode
from datetime import datetime
from math import ceil

class EcommerceAdminDashboard(http.Controller):
    @http.route('/ecommerce_admin/order', type='http', auth='user', website=True)
    def ecommerce_order_list(self, customer_id=None, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')

        domain = []
        if customer_id:
            domain.append(('partner_id', '=', int(customer_id)))

        orders = request.env['sale.order'].sudo().search(domain, order="date_order desc", limit=50)
        return request.render('ecommerce_admin.order_list_template', {
            'orders': orders,
            'filter_customer_id': int(customer_id) if customer_id else None,
        })

    @http.route('/ecommerce_admin/order/<int:order_id>', type='http', auth='user', website=True)
    def ecommerce_order_detail(self, order_id, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')
        order = request.env['sale.order'].sudo().browse(order_id)
        return request.render('ecommerce_admin.order_detail_template', {
            'order': order,
        })
    @http.route('/ecommerce_admin/customers', type='http', auth='user', website=True)
    def ecommerce_customers(self, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')
        portal_group = request.env.ref('base.group_portal')
        customers = request.env['res.users'].sudo().search([
            ('groups_id', 'in', [portal_group.id])
        ], order='name asc')
        return request.render('ecommerce_admin.customer_list_template', {
            'customers': customers,
        })
    def _is_admin(self):
        return request.env.user.has_group('ecommerce_admin.group_ecommerce_admin')

    @http.route('/ecommerce_admin/dashboard', auth='user', website=True)
    def dashboard(self, **kw):
        if not self._is_admin():
            return request.redirect('/web/login')
        return request.render('ecommerce_admin.dashboard_template', {})

    PRODUCTS_PER_PAGE = 10
    
    @http.route('/ecommerce_admin/products', auth='user', website=True)
    def products(self, **kw):
        if not self._is_admin():
            return request.redirect('/web/login')
        
        search_query = kw.get('search', '')
        category_id = kw.get('category', '')
        current_page = int(kw.get('page', 1))
        
        domain = []
        if search_query:
            domain.append(('name', 'ilike', search_query))
        if category_id:
            domain.append(('public_categ_ids', '=', int(category_id)))
        
        product_count = request.env['product.template'].sudo().search_count(domain)
        page_count = ceil(product_count / self.PRODUCTS_PER_PAGE)
        
        offset = (current_page - 1) * self.PRODUCTS_PER_PAGE
        products = request.env['product.template'].sudo().search(
            domain, 
            limit=self.PRODUCTS_PER_PAGE, 
            offset=offset
        )
        
        categories = request.env['product.public.category'].sudo().search([])
        
        return request.render('ecommerce_admin.product_list', {
            'products': products,
            'categories': categories,
            'search_query': search_query,
            'selected_category': category_id and int(category_id) or None,
            'format_date': lambda dt: dt.strftime('%b %d, %Y') if dt else '',
            'current_page': current_page,
            'page_count': page_count,
            'range': range
        })


    @http.route('/ecommerce_admin/products/create', auth='public',csrf=False, cors="*", website=True, methods=["GET", "POST"])
    def create_product(self, **post):
        if not self._is_admin():
            return request.redirect('/web/login')

        ProductCategory = request.env['product.public.category'].sudo()
        categories = ProductCategory.search([])

        if http.request.httprequest.method == 'POST':
            name = post.get('name')
            list_price = float(post.get('list_price', 0))
            standard_price = float(post.get('standard_price', 0))
            category_id = int(post.get('public_categ_id', 0)) or False
            image_file = post.get('image_1920')

            image_data = False
            if image_file and hasattr(image_file, 'read'):
                image_data = b64encode(image_file.read())

            product_vals = {
                'name': name,
                'list_price': list_price,
                'standard_price': standard_price,
                'is_published': True,
                'public_categ_ids': [(6, 0, [category_id])] if category_id else [],
            }
            if image_data:
                product_vals['image_1920'] = image_data

            request.env['product.template'].sudo().create(product_vals)
            return request.redirect('/ecommerce_admin/products')

        return request.render('ecommerce_admin.product_create', {
            'categories': categories,
        })


    @http.route('/ecommerce_admin/products/<int:product_id>', auth='user', website=True)
    def product_detail(self, product_id, **kw):
        if not self._is_admin():
            return request.redirect('/web/login')
        
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.redirect('/ecommerce_admin/products')
        
        return request.render('ecommerce_admin.product_detail', {
            'product': product,
            'format_date': lambda dt: dt.strftime('%b %d, %Y') if dt else ''
        })

    @http.route('/ecommerce_admin/products/<int:product_id>/edit', auth='user', website=True)
    def product_edit(self, product_id, **kw):
        if not self._is_admin():
            return request.redirect('/web/login')
        
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.redirect('/ecommerce_admin/products')
        
        categories = request.env['product.public.category'].sudo().search([])
        
        return request.render('ecommerce_admin.product_edit', {
            'product': product,
            'categories': categories
        })

    @http.route('/ecommerce_admin/products/<int:product_id>/update', auth='public', csrf=False, cors="*", website=True, methods=['POST'])
    def product_update(self, product_id, **post):
        if not self._is_admin():
            return request.redirect('/web/login')

        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.redirect('/ecommerce_admin/products')

        # Fetch fields from request
        name = request.params.get('name')
        list_price = request.params.get('list_price')
        standard_price = request.params.get('standard_price')
        category_ids = request.httprequest.form.getlist('public_categ_ids')

        # Safely convert price fields to float
        try:
            list_price = float(list_price or 0)
        except ValueError:
            list_price = 0.0

        try:
            standard_price = float(standard_price or 0)
        except ValueError:
            standard_price = 0.0

        # Prepare update values
        update_vals = {
            'name': name,
            'list_price': list_price,
            'standard_price': standard_price,
            'public_categ_ids': [(6, 0, [int(cid) for cid in category_ids if cid.isdigit()])],
        }

        # Handle image upload
        image_file = request.httprequest.files.get('image_1920')
        if image_file and hasattr(image_file, 'read'):
            update_vals['image_1920'] = b64encode(image_file.read())

        # Update the product
        product.write(update_vals)

        return request.redirect('/ecommerce_admin/products/%s' % product_id)
