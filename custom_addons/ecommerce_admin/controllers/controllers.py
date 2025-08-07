# ecommerce_admin/controllers/website_sale_custom.py

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo import http

class WebsiteSaleCustom(WebsiteSale):
    def _shop_lookup_products(self, attrib_set, options, post, search, website):
        # Call the original fuzzy search
        product_count, details, fuzzy_search_term = website._search_with_fuzzy(
            "products_only",
            search,
            limit=None,
            order=self._get_search_order(post),
            options=options
        )

        # Extract search result (product.template recordset)
        search_result = details[0].get('results', request.env['product.template']).with_context(bin_size=True)

        # ✅ Filter out unpublished products
        search_result = search_result.filtered(lambda p: p.website_published)

        return fuzzy_search_term, product_count, search_result
