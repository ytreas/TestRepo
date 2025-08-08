from odoo import http
from odoo.http import request
from base64 import b64encode
from datetime import datetime
from math import ceil
def build_category_tree(categories):
    categories_dict = {cat.id: {
        'id': cat.id,
        'name': cat.display_name,
        'children': []
    } for cat in categories}
    
    tree = []
    for cat in categories:
        node = categories_dict[cat.id]
        if cat.parent_id and cat.parent_id.id in categories_dict:
            categories_dict[cat.parent_id.id]['children'].append(node)
        else:
            tree.append(node)
    return tree
class EcommerceAdminDashboard(http.Controller):
    @http.route('/ecommerce_admin/order', type='http', auth='user', website=True)
    def ecommerce_order_list(self, customer_id=None, status=None, search=None, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')

        domain = []
        if customer_id:
            domain.append(('partner_id', '=', int(customer_id)))
        if status:
            domain.append(('state', '=', status))
        if search:
            domain.append(('name', 'ilike', search))

        orders = request.env['sale.order'].sudo().search(domain, order="date_order desc", limit=50)
        return request.render('ecommerce_admin.order_list_template', {
            'orders': orders,
            'filter_customer_id': int(customer_id) if customer_id else None,
            'filter_status': status,
            'search_term': search,
        })


    @http.route('/ecommerce_admin/order/<int:order_id>', type='http', auth='user', website=True)
    def ecommerce_order_detail(self, order_id, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')
        order = request.env['sale.order'].sudo().browse(order_id)

        # Check if there is at least one picking NOT done or canceled (delivery possible)
        can_deliver = any(p.state not in ['done', 'cancel'] for p in order.picking_ids)

        return request.render('ecommerce_admin.order_detail_template', {
            'order': order,
            'can_deliver': can_deliver,
        })

    @http.route('/ecommerce_admin/order/<int:order_id>/pay', type='http', auth='user', methods=['POST'], csrf=False)
    def ecommerce_order_pay(self, order_id, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')
        order = request.env['sale.order'].sudo().browse(order_id)
        if order.state == 'draft':
            order.action_confirm()
        return request.redirect(f'/ecommerce_admin/order/{order_id}')
    @http.route('/ecommerce_admin/order/<int:order_id>/deliver', type='http', auth='user', methods=['POST'], csrf=False)
    def ecommerce_order_deliver(self, order_id, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')

        order = request.env['sale.order'].sudo().browse(order_id)
        
        # First confirm the sale order if it's in draft state
        if order.state == 'draft':
            order.action_confirm()
        
        # Process all pickings that aren't done or canceled
        for picking in order.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel']):
            # Check availability
            picking.action_assign()
            
            # Set quantities done for each move line
            for move in picking.move_ids.filtered(lambda m: m.state not in ['done', 'cancel']):
                if not move.move_line_ids:
                    # If no move lines exist, create one
                    move._generate_serial_move_line_commands()
                for move_line in move.move_line_ids:
                    qty = move.product_uom_qty
                    if 'qty_done' in move_line._fields:
                        move_line.qty_done = qty
                    elif 'quantity_done' in move_line._fields:
                        move_line.quantity_done = qty
            
            # Validate the picking
            if picking.state != 'done':
                try:
                    picking.button_validate()
                except Exception as e:
                    # If there's an error (like backorder needed), force validate
                    picking.with_context(skip_backorder=True, skip_overprocessed_check=True)._action_done()
        
        return request.redirect(f'/ecommerce_admin/order/{order_id}')





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


    @http.route('/ecommerce_admin/products/create', auth='public', csrf=False, cors="*", website=True, methods=["GET", "POST"])
    def create_product(self, **post):
        if not request.env.user.has_group('ecommerce_admin.group_ecommerce_admin'):
            return request.redirect('/web/login')

        ProductCategory = request.env['product.category'].sudo()
        PublicCategory = request.env['product.public.category'].sudo()
        categories = ProductCategory.search([])
        public_categories = PublicCategory.search([])

        if request.httprequest.method == 'POST':
            name = post.get('name')
            list_price = float(post.get('list_price', 0))
            standard_price = float(post.get('standard_price', 0))
            internal_categ_id = int(post.get('internal_categ_id', 0)) or False
            public_categ_id = int(post.get('public_categ_id', 0)) or False
            image_file = post.get('image_1920')

            image_data = False
            if image_file and hasattr(image_file, 'read'):
                image_data = b64encode(image_file.read())

            product_vals = {
                'name': name,
                'list_price': list_price,
                'standard_price': standard_price,
                'is_published': True,
            }

            if internal_categ_id:
                product_vals['categ_id'] = internal_categ_id
            if public_categ_id:
                product_vals['public_categ_ids'] = [(6, 0, [public_categ_id])]
            if image_data:
                product_vals['image_1920'] = image_data

            request.env['product.template'].sudo().create(product_vals)
            return request.redirect('/ecommerce_admin/products')

        return request.render('ecommerce_admin.product_create', {
            'categories': categories,
            'public_categories': public_categories,
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

    @http.route('/ecommerce_admin/products/<int:product_id>/toggle_publish', type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def toggle_product_publish(self, product_id, **kw):
        if not self._is_admin():
            return request.redirect('/web/login')
        
        product = request.env['product.template'].sudo().browse(product_id)
        if product.exists():
            # Toggle the boolean field
            product.is_published = not product.is_published
        return request.redirect(f'/ecommerce_admin/products/{product_id}')

    @http.route('/ecommerce_admin/products/<int:product_id>/edit', auth='user', website=True)
    def product_edit(self, product_id, **kw):
        if not self._is_admin():
            return request.redirect('/web/login')

        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.redirect('/ecommerce_admin/products')

        categories = request.env['product.category'].sudo().search([])
        public_categories = request.env['product.public.category'].sudo().search([])

        return request.render('ecommerce_admin.product_edit', {
            'product': product,
            'categories': categories,
            'public_categories': public_categories,
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
        internal_categ_id = request.params.get('categ_id')
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
            'categ_id': internal_categ_id,
        }

        # Handle image upload
        image_file = request.httprequest.files.get('image_1920')
        if image_file and hasattr(image_file, 'read'):
            update_vals['image_1920'] = b64encode(image_file.read())

        # Update the product
        product.write(update_vals)

        return request.redirect('/ecommerce_admin/products/%s' % product_id)
    
    @http.route('/ecommerce_admin/categories', type='http', auth='user', website=True)
    def category_list(self, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')

        search_term = kwargs.get('search', '')
        domain = []
        if search_term:
            domain = ['|', ('name', 'ilike', search_term), ('display_name', 'ilike', search_term)]

        categories = request.env['product.public.category'].sudo().search(domain, order='parent_id, sequence, name')

        tree = build_category_tree(categories)

        return request.render('ecommerce_admin.category_list', {
            'categories': tree,
            'search_term': search_term,
        })


    @http.route('/ecommerce_admin/categories/create', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def category_create(self, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')

        CategoryPublic = request.env['product.public.category']
        CategoryInternal = request.env['product.category']
        
        # Get all potential parent categories for the dropdown
        parent_categories = CategoryPublic.sudo().search([])
        
        # Handle form submission
        if request.httprequest.method == 'POST':
            try:
                vals = {
                    'name': kwargs.get('name'),
                    'parent_id': int(kwargs.get('parent_id')) if kwargs.get('parent_id') else False,
                    'sequence': int(kwargs.get('sequence', 10)),
                }
                
                # Create public category
                new_category = CategoryPublic.sudo().create(vals)
                
                # Find internal parent category if specified
                internal_parent_id = False
                if new_category.parent_id:
                    internal_parent = CategoryInternal.sudo().search(
                        [('name', '=', new_category.parent_id.name)], 
                        limit=1
                    )
                    if internal_parent:
                        internal_parent_id = internal_parent.id
                
                # Create corresponding internal category
                CategoryInternal.sudo().create({
                    'name': vals['name'],
                    'parent_id': internal_parent_id,
                    # 'sequence': vals['sequence'],
                })
                
                return request.redirect('/ecommerce_admin/categories')
                
            except Exception as e:
                # _logger.error("Failed to create category: %s", str(e))
                # Keep form values on error
                return request.render('ecommerce_admin.category_create', {
                    'parent_categories': parent_categories,
                    'error': str(e),
                    'form_data': kwargs
                })

        # For GET request, show empty form
        return request.render('ecommerce_admin.category_create', {
            'parent_categories': parent_categories
        })


    @http.route('/ecommerce_admin/categories/<int:category_id>', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def category_detail(self, category_id, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')

        CategoryPublic = request.env['product.public.category']
        CategoryInternal = request.env['product.category']
        category = CategoryPublic.sudo().browse(category_id)
        
        if not category.exists():
            return request.redirect('/ecommerce_admin/categories')

        # Handle POST request (form submission)
        if request.httprequest.method == 'POST':
            try:
                vals = {
                    'name': kwargs.get('name'),
                    'parent_id': int(kwargs.get('parent_id')) if kwargs.get('parent_id') else False,
                    'sequence': int(kwargs.get('sequence', 10)),
                }
                old_name = category.name
                # Update public category
                category.write(vals)
                
                # Find internal parent category if specified
                internal_parent_id = False
                if category.parent_id:
                    internal_parent = CategoryInternal.sudo().search(
                        [('name', '=', category.parent_id.name)], 
                        limit=1
                    )
                    if internal_parent:
                        internal_parent_id = internal_parent.id
                print("--------------------->",old_name)
                # Find or create corresponding internal category
                internal_category = CategoryInternal.sudo().search(
                    [('name', '=', old_name)], 
                    limit=1
                )
                print(f"Internal category found: {internal_category}")
                if internal_category:
                    # Update existing internal category
                    internal_category.write({
                        'name': vals['name'],
                        'parent_id': internal_parent_id,
                        # 'sequence': vals['sequence'],
                    })
                else:
                    # Create new internal category
                    CategoryInternal.sudo().create({
                        'name': vals['name'],
                        'parent_id': internal_parent_id,
                        # 'sequence': vals['sequence'],
                    })
                
                return request.redirect('/ecommerce_admin/categories')
                
            except Exception as e:
                # _logger.error("Failed to update category: %s", str(e))
                # Keep form values on error
                return request.render('ecommerce_admin.category_detail', {
                    'category': category,
                    'parent_category': category.parent_id,
                    'child_categories': category.child_id,
                    'error': str(e)
                })

        # For GET request, render the form
        return request.render('ecommerce_admin.category_detail', {
            'category': category,
            'parent_category': category.parent_id,
            'child_categories': category.child_id,
        })

    @http.route('/ecommerce_admin/categories/<int:category_id>/delete', type='http', auth='user', website=True)
    def category_delete(self, category_id, **kwargs):
        if not self._is_admin():
            return request.redirect('/web/login')

        category = request.env['product.public.category'].sudo().browse(category_id)
        if category:
            # Also find and delete matching product.category
            product_cat = request.env['product.category'].sudo().search([('name', '=', category.name)])
            product_cat.unlink()
            category.unlink()
        return request.redirect('/ecommerce_admin/categories')

    @http.route('/ecommerce_admin/discounts', type='http', auth='user', website=True)
    def list_discounts(self):
        if not self._is_admin():
            return request.redirect('/web/login')

        # Get only items from pricelist ID 4
        pricelist = request.env['product.pricelist'].sudo().browse(3)
        return request.render('ecommerce_admin.discount_list', {
            'items': pricelist.item_ids
        })

    @http.route('/ecommerce_admin/discounts/create', type='http', auth='public', cors='*', csrf=False, website=True, methods=['GET', 'POST'])
    def create_discount(self, **post):
        if not self._is_admin():
            return request.redirect('/web/login')

        pricelist = request.env['product.pricelist'].sudo().browse(3)
        base_pricelist = request.env['product.pricelist'].sudo().browse(1)
        
        if request.httprequest.method == 'POST':
            request.env['product.pricelist.item'].sudo().create({
                'pricelist_id': pricelist.id,
                'applied_on': post.get('display_applied_to'),
                'product_tmpl_id': int(post['product_tmpl_id']) if post.get('display_applied_to') == '1_product' else False,
                'categ_id': int(post['categ_id']) if post.get('display_applied_to') == '2_product_category' else False,
                'base': 'pricelist',
                'base_pricelist_id': 1,
                'compute_price': 'percentage',
                'percent_price': float(post.get('percent_price')),
                'date_start': post.get('date_start'),
                'date_end': post.get('date_end'),
            })
            return request.redirect('/ecommerce_admin/discounts')

        currencies = request.env['res.currency'].sudo().search([])
        products = request.env['product.template'].sudo().search([])
        categories = request.env['product.category'].sudo().search([])
        return request.render('ecommerce_admin.discount_create', {
            'currencies': currencies,
            'products': products,
            'categories': categories,
        })

    @http.route('/ecommerce_admin/discounts/delete/<int:item_id>', type='http', auth='user', website=True)
    def delete_discount(self, item_id):
        if not self._is_admin():
            return request.redirect('/web/login')

        item = request.env['product.pricelist.item'].sudo().browse(item_id)
        if item.exists() and item.pricelist_id.id == 3:
            item.unlink()
        return request.redirect('/ecommerce_admin/discounts')

    @http.route('/ecommerce_admin/discounts/edit/<int:item_id>', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def edit_discount(self, item_id, **post):
        if not self._is_admin():
            return request.redirect('/web/login')

        item = request.env['product.pricelist.item'].sudo().browse(item_id)
        if not item.exists() or item.pricelist_id.id != 3:
            return request.redirect('/ecommerce_admin/discounts')

        if request.httprequest.method == 'POST':
            item.write({
                'applied_on': post.get('display_applied_to'),
                'product_tmpl_id': int(post['product_tmpl_id']) if post.get('display_applied_to') == '1_product' else False,
                'categ_id': int(post['categ_id']) if post.get('display_applied_to') == '2_product_category' else False,
                'percent_price': float(post.get('percent_price')),
                'date_start': post.get('date_start'),
                'date_end': post.get('date_end'),
            })
            return request.redirect('/ecommerce_admin/discounts')

        currencies = request.env['res.currency'].sudo().search([])
        products = request.env['product.template'].sudo().search([])
        categories = request.env['product.category'].sudo().search([])
        return request.render('ecommerce_admin.discount_edit', {
            'item': item,
            'currencies': currencies,
            'products': products,
            'categories': categories,
        })