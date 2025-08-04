# -*- coding: utf-8 -*-
# Copyright (c) 2019-Present Droggol. (<https://www.droggol.com/>)

import hashlib
import json
import string

from collections import defaultdict

from odoo import http
from odoo.http import request

from odoo.osv import expression

from odoo.addons.website_sale_wishlist.controllers.main import WebsiteSaleWishlist
from odoo.addons.website_sale.controllers.main import WebsiteSale


class DroggolThemeCommon(http.Controller):

    @http.route('/shop/all_brands', type='http', auth='public', website=True)
    def all_brands(self, **args):
        alphabet_range = string.ascii_uppercase
        series = defaultdict(list)
        series.update((alphabet, []) for alphabet in alphabet_range)
        brands = request.env['dr.product.brand'].search(request.website.website_domain(), order="name")
        for brand in brands:
            first_char = str.upper(brand.name[:1])
            series[first_char].append(brand)
        disable_grouping = request.env['ir.config_parameter'].sudo().get_param('theme_prime.brand_grouping_disable')
        if disable_grouping:
            series = {'all': brands}
        return request.render('droggol_theme_common.all_brands', {
            'disable_grouping': disable_grouping,
            'series': series
        })


class DroggolWishlist(WebsiteSaleWishlist):
    @http.route('/droggol_theme_common/wishlist_general', auth="public", type='json', website=True)
    def wishlist_general(self, product_id=False, **post):
        res = {}
        if product_id:
            res['wishlist_id'] = self.add_to_wishlist(product_id).id
        res.update({
            'products': request.env['product.wishlist'].with_context(display_default_code=False).current().mapped('product_id').ids,
            'name': request.env['product.product'].browse(product_id).name
        })
        return res


class DroggolWebsiteSale(WebsiteSale):

    @http.route(['/shop/cart'], type='http', auth='public', website=True, sitemap=False)
    def cart(self, access_token=None, revive='', **post):
        res = super(DroggolWebsiteSale, self).cart(access_token=access_token, revive=revive, **post)
        if post.get('type') == 'dr_sale_cart_request':
            order = request.website.sale_get_order()
            if order and order.state != 'draft':
                request.session['sale_order_id'] = None
                order = request.website.sale_get_order()
            return request.render('droggol_theme_common.dr_sale_cart_sidebar', {'order': order}, headers={'Cache-Control': 'no-cache'})
        return res

    @http.route(['/droggol_theme_common/get_website_category'], type='json', auth="public", website=True)
    def get_website_category(self, **post):
        categories = request.website._get_website_category()
        if not categories:
            return []
        return categories.read(['name', 'id'])

    @http.route()
    def products_autocomplete(self, term, options={}, **kwargs):
        response = super(DroggolWebsiteSale, self).products_autocomplete(term, options=options, **kwargs)
        if options.get('category'):
            for result in response.get('products'):
                result['website_url'] = result.get('website_url') + '?category=%s' % options.get('category')
        return response


class productSnippet(http.Controller):

    @http.route('/product_snippet/get_category_by_name', type='http', website=True)
    def get_category_by_name(self, term='', category_id=False, **post):
        domain = expression.AND([request.website.website_domain(), [('name', 'ilike', (term or ''))]])
        if category_id:
            domain = expression.AND([domain, [('id', 'child_of', int(category_id))]])
        result = request.env['product.public.category'].search_read(domain, fields=['name', 'display_name', 'id'], limit=10)
        return json.dumps(result)

    @http.route('/product_snippet/get_product_by_name', type='http', website=True)
    def get_product_by_name(self, term='', **post):
        domains = [request.website.sale_product_domain(), [('website_published', '=', True)]]
        subdomains = [
            [('name', 'ilike', (term or ''))],
            [('product_variant_ids.default_code', 'ilike', (term or ''))]
        ]
        domains.append(expression.OR(subdomains))
        fields = ['description_sale']
        result = self._get_products(expression.AND(domains), fields, 25, 'is_published desc, website_sequence ASC, id desc')
        return json.dumps(result)

    @http.route('/droggol_theme_common/get_brands', type='json', auth='public', website=True)
    def get_brands(self, fields=['id'], options={}):
        return request.env['dr.product.brand'].search_read(request.website.website_domain(), limit=options.get('limit', 12), fields=fields)

    @http.route('/droggol_theme_common/get_mega_menu_categories', type='json', auth='public', website=True)
    def get_mega_menu_categories(self, options={}, **kwargs):
        categoryIDs = options.get('categoryIDs', [])
        domain = expression.AND([request.website.website_domain(), [('id', 'in', categoryIDs)]])
        return request.env['product.public.category'].search_read(domain=domain, fields=['name', 'display_name', 'id'])

    @http.route('/droggol_theme_common/get_top_categories', type='json', auth='public', website=True)
    def get_top_categories(self, options={}):
        params = options.get('params')
        result = []
        pricelist = request.website.get_current_pricelist()
        website_sale_domain = request.website.sale_product_domain()
        FieldMonetary = request.env['ir.qweb.field.monetary']
        monetary_options = {
            'display_currency': pricelist.currency_id,
        }
        if params:
            categoryIDs = params.get('categoryIDs')
            if categoryIDs:
                category_names = {i['id']: i['name'] for i in self._get_category_names(categoryIDs)}
                # Update categoryIDs if already set category moved to other website
                categoryIDs = category_names.keys()
                params['categoryIDs'] = categoryIDs
                categories = self._get_products_for_top_categories(params)
                for category_id in categoryIDs:
                    category_data = {}
                    product_ids = categories.get(category_id)
                    category_data['name'] = category_names.get(category_id)
                    category_data['id'] = category_id
                    category_data['website_url'] = '/shop/category/' + str(category_id)
                    category_data['productIDs'] = product_ids
                    final_domain = expression.AND([website_sale_domain, [('public_categ_ids', 'child_of', category_id)]])
                    product_price = request.env['product.template'].with_context(pricelist=pricelist.id).read_group(final_domain, fields=['min_price:min(list_price)'], groupby=['active'])
                    if len(product_price):
                        min_price = request.website._convert_currency_price(product_price[0].get('min_price'), rounding_method=lambda amt: round(amt, 2))
                        category_data['min_price'] = FieldMonetary.value_to_html(min_price, monetary_options)
                    result.append(category_data)
        return result

    @http.route('/droggol_theme_common/get_products_by_category', type='json', auth='public', website=True)
    def get_products_by_category(self, domain, fields=[], options={}, **kwargs):
        final_domain = expression.AND([[('website_published', '=', True)], domain])
        result = {
            'products': self._get_products(domain=final_domain, fields=fields, order=options.get('order', False), limit=options.get('limit', False)),
        }
        result.update(self._get_shop_related_data(options))
        if (options.get('get_categories')):
            # get category names for snippet
            result['categories'] = self._get_category_names(options.get('categoryIDs'))
        return result

    def _get_category_names(self, categoryIDs):
        domain = expression.AND([request.website.website_domain(), [('id', 'in', categoryIDs)]])
        return request.env['product.public.category'].search_read(domain, fields=['name', 'display_name', 'id'])

    @http.route('/droggol_theme_common/get_products_data', type='json', auth='public', website=True)
    def get_products_data(self, domain, fields=[], options={},  limit=25, order=None, **kwargs):
        result = {
            'products': self._get_products(domain, fields, limit, order),
        }
        result.update(self._get_shop_related_data(options))
        return result

    @http.route('/droggol_theme_common/get_products_by_collection', type='json', auth='public', website=True)
    def get_products_by_collection(self, fields=[], limit=25, order=None, options={}, **kwargs):
        collections = options.get('collections')
        result = []
        shop_config_params = self.get_shop_config()
        for collection in collections:
            res = {}
            res['title'] = collection.get('title', '')
            res['is_rating_active'] = shop_config_params.get('is_rating_active', False)
            res['products'] = self._get_products_from_collection(collection.get('data'), fields, limit, order)
            result.append(res)
        return result

    @http.route('/droggol_theme_common/get_single_product_data', type='json', auth='public', website=True)
    def get_single_product_data(self, options, **kwargs):
        productID = options.get('productID')
        domain = expression.AND([request.website.sale_product_domain(), [('id', '=', productID)]])
        product = request.env['product.template'].search(domain, limit=1)
        # If moved to another website or delete
        if not product:
            return []
        values = self._prepare_product_values(product, **kwargs)
        return request.env["ir.ui.view"].render_template('droggol_theme_common.dr_product_right_panel', values=values)

    @http.route('/droggol_theme_common/get_quick_view_html', type='json', auth='public', website=True)
    def get_quick_view_html(self, options, **kwargs):
        productID = options.get('productID')
        variantID = options.get('variantID')
        product = False
        if variantID:
            productID = request.env['product.product'].browse(variantID).product_tmpl_id.id

        domain = expression.AND([request.website.sale_product_domain(), [('id', '=', productID)]])
        product = request.env['product.template'].search(domain, limit=1)
        # If moved to another website or delete
        if not product:
            return []

        # If request ask `add_if_single_variant` param
        # Do not return if there is only one varient
        is_single_product = options.get('add_if_single_variant') and product.product_variant_count == 1

        values = self._prepare_product_values(product, **kwargs)
        if options.get('mini'):
            values['auto_add_product'] = is_single_product
            return request.env["ir.ui.view"].render_template('droggol_theme_common.product_mini', values=values)
        return request.env["ir.ui.view"].render_template('droggol_theme_common.product', values=values)

    @http.route('/droggol_theme_common/get_shop_config', type='json', auth='public', website=True)
    def get_shop_config(self):
        Website = request.website
        result = {
            'is_rating_active': Website.viewref('website_sale.product_comment').active,
            'is_buy_now_active': Website.viewref('website_sale.product_buy_now').active,
            'is_multiplier_active': Website.viewref('website_sale.product_quantity').active,
            'is_wishlist_active': Website.viewref('website_sale_wishlist.add_to_wishlist').active,
            'is_comparison_active': Website.viewref('website_sale_comparison.add_to_compare').active,
            'is_wishlist_installed': False,
            'is_compare_installed': False,
        }
        modules = request.env['ir.module.module'].sudo().search(expression.OR([[('name', '=', 'website_sale_wishlist')], [('name', '=', 'website_sale_comparison')]]))
        for module in modules:
            if module.state == 'installed':
                if module.name == 'website_sale_comparison':
                    result['is_compare_installed'] = True
                if module.name == 'website_sale_wishlist':
                    result['is_wishlist_installed'] = True
        return result

    @http.route('/droggol_theme_common/_get_products_from_collection', type='json', auth='public', website=True)
    def _get_products_from_collection(self, collection, fields=[], limit=25, order=None, **kwargs):
        selection_type = collection.get('selectionType')
        if selection_type == 'manual':
            return self._get_d_products_manually(collection, fields, limit, order)
        elif selection_type == 'advance':
            return self._get_d_products_advance(collection, fields)

    # ----------------------------------------------------------
    # Helper methods
    # ----------------------------------------------------------

    def _get_products(self, domain=None, fields=[], limit=25, order=None):
        pricelist = request.website.get_current_pricelist()
        rating_in_fields = False
        offer_in_fields = False
        website_sale_domain = request.website.sale_product_domain()
        final_domain = expression.AND([website_sale_domain, domain])
        products = request.env['product.template'].with_context(pricelist=pricelist.id).search(final_domain, limit=limit, order=order)
        default_fields = ['id', 'name', 'website_url']
        fields = set(default_fields + fields)

        # rating is not a real field
        if 'rating' in fields:
            rating_in_fields = True
            fields.remove('rating')
        # rating is not a real field
        if 'offer_data' in fields:
            offer_in_fields = True
            fields.remove('offer_data')

        result = products.read(fields)
        FieldMonetary = request.env['ir.qweb.field.monetary']
        monetary_options = {
            'display_currency': pricelist.currency_id,
        }

        for res_product, product in zip(result, products):
            combination_info = product._get_combination_info(only_template=True)
            res_product.update(combination_info)
            res_product['price'] = FieldMonetary.value_to_html(res_product['price'], monetary_options)
            res_product['list_price'] = FieldMonetary.value_to_html(res_product['list_price'], monetary_options)
            res_product['product_variant_id'] = product._get_first_possible_variant_id()

            sha = hashlib.sha1(str(getattr(product, '__last_update')).encode('utf-8')).hexdigest()[0:7]
            # Images
            res_product['img_small'] = '/web/image/product.template/' + str(product.id) + '/image_256?unique=' + sha
            res_product['img_medium'] = '/web/image/product.template/' + str(product.id) + '/image_512?unique=' + sha
            res_product['img_large'] = '/web/image/product.template/' + str(product.id) + '/image_1024?unique=' + sha

            # short Description
            if 'description_sale' in fields:
                description = res_product.get('description_sale')
                res_product['short_description'] = description[:200] + '...' if description and len(description) > 200 else description or False
            # label and color
            if 'dr_label_id' in fields and product.dr_label_id:
                res_product['label'] = product.dr_label_id.name
                res_product['label_color'] = product.dr_label_id.color
            # rating
            if offer_in_fields:
                offer = product._get_product_pricelist_offer()
                if offer:
                    rule = offer.get('rule')
                    res_product['offer_data'] = {
                        'date_end': offer.get('date_end'),
                        'offer_msg': rule.offer_msg,
                        'offer_finish_msg': rule.offer_finish_msg
                    }

            if rating_in_fields:
                res_product['rating'] = self._get_rating_template(product.rating_avg)
            # images
            if 'product_template_image_ids' in fields:
                res_product['images'] = product.product_template_image_ids.ids
            # website_category
            if 'public_categ_ids' in fields and product.public_categ_ids:
                first_category = product.public_categ_ids[0]
                res_product['category_info'] = {
                    'name': first_category.name,
                    'id': first_category.id,
                    'website_url': 'shop/category/' + str(first_category.id),
                }

        return result

    def _get_rating_template(self, rating_avg, rating_count=False):
        return request.env["ir.ui.view"].render_template('droggol_theme_common.d_rating_widget_stars_static', values={
            'rating_avg': rating_avg,
            'rating_count': rating_count,
        })

    def _get_shop_related_data(self, options):
        shop_data = {}
        if (options.get('shop_config_params')):
            shop_data['shop_config_params'] = self.get_shop_config()
        if (options.get('wishlist_enabled')) and shop_data.get('shop_config_params', {}).get('is_wishlist_active'):
            shop_data['wishlist_products'] = request.env['product.wishlist'].with_context(display_default_code=False).current().mapped('product_id').ids
        return shop_data

    def _get_d_products_manually(self, collection, fields, limit, order, **kwargs):
        domain = [['id', 'in', collection.get('productIDs', [])]]
        return self._get_products(domain, fields, limit, order)

    def _get_d_products_advance(self, collection, fields, **kwargs):
        domain_params = collection.get('domain_params')
        domain = domain_params.get('domain')
        limit = domain_params.get('limit', 25)
        order = domain_params.get('sortBy', None)
        return self._get_products(domain, fields, limit, order)

    def _get_products_for_top_categories(self, params):
        result = {}
        categoryIDs = params.get('categoryIDs')
        order = params.get('sortBy')
        operator = '='
        if params.get('includesChild'):
            operator = 'child_of'
        initial_domain = expression.AND([request.website.website_domain(), [('website_published', '=', True)]])
        pricelist = request.website.get_current_pricelist()
        for id in categoryIDs:
            domain = expression.AND([initial_domain, [['public_categ_ids', operator, id]]])
            products = request.env['product.template'].with_context(pricelist=pricelist.id).search_read(domain=domain, fields=['id'], limit=3, order=order)
            result[id] = [product['id'] for product in products]
        return result

    def _prepare_product_values(self, product, **kwargs):
        add_qty = int(kwargs.get('add_qty', 1))

        product_context = dict(request.env.context, quantity=add_qty,
                               active_id=product.id,
                               partner=request.env.user.partner_id)

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attrib_set = {v[1] for v in attrib_values}

        pricelist = request.website.get_current_pricelist()

        if not product_context.get('pricelist'):
            product_context['pricelist'] = pricelist.id
            product = product.with_context(product_context)

        # Needed to trigger the recently viewed product rpc
        view_track = request.website.viewref("website_sale.product").track
        result = self.get_shop_config()
        if result.get('is_rating_active'):
            result['rating'] = self._get_rating_template(product.rating_avg, product.rating_count)
        result.update({
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'main_object': product,
            'product': product,
            'add_qty': add_qty,
            'view_track': view_track,
            'd_url_root': request.httprequest.url_root[:-1],
        })
        return result
