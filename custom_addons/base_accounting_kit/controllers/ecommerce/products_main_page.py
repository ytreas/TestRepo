from odoo import http, _
from odoo.http import request
import math
from odoo.addons.base_accounting_kit.models.ecommerce import utils

import os
from dotenv import load_dotenv

load_dotenv()
ECOMMERCE_MAIN_DOMAIN = os.getenv("ECOMMERCE_MAIN_DOMAIN", "http://lekhaplus.com/")


class ProductMainPAge(http.Controller):

    @http.route(
        [
            "/products",
            "/products/category/<model('product.category'):category>",
            # "/products/vendor/<model('res.company'):vendor>",
        ],
        methods=["GET"],
        type="http",
        website=True,
        auth="public",
    )
    def get_products(
        self,
        page=1,
        category=None,
        attribute_variants=None,
        page_size=20,
        price=None,
        sort_by=None,
        vendor=None,
        v=None,
        **kwargs
    ):
        # Ensure default page and page_size values
        page = int(page) or 1
        page_size = int(page_size) or 20
        offset = (page - 1) * page_size
        origin_url = utils.EcomUtils.get_current_origin()
        parent_company = (
            request.env["res.company"]
            .sudo()
            .search([("website", "=", origin_url["origin_url"])], limit=1)
        )
        # print('origin_url["origin_url"] == ECOMMERCE_MAIN_DOMAIN',origin_url["origin_url"] == ECOMMERCE_MAIN_DOMAIN)
        if origin_url["origin_url"] == ECOMMERCE_MAIN_DOMAIN:
            domain = [
                ("publish", "=", True),
                ("saleable_qty", ">", 0),
            ]
            product_categories = request.env["product.category"].sudo().search([])
            product_attributes = request.env["cp.attribute"].sudo().search([])

        else:
            domain = [
                ("publish", "=", True),
                ("saleable_qty", ">", 0),
                # '|',
                ("company_id.parent_id", "=", parent_company.id),
                # ("company_id", "=", parent_company.id),
            ]
            product_categories = (
                request.env["product.category"]
                .sudo()
                .search([("company_id", "=", parent_company.id)])
            )
            product_attributes = (
                request.env["cp.attribute"]
                .sudo()
                .search([("company_id", "=", parent_company.id)])
            )

        # product_categories = request.env["product.category"].sudo().search([])
        # product_attributes = request.env["cp.attribute"].sudo().search([])

        branch_products_template = request.env["product.custom.price"]

        keyword = kwargs.get("q", "").strip()

        # price
        min_price = max_price = None
        if price:
            try:
                if "-" in price:
                    parts = price.split("-")
                    if price.startswith("-"):
                        max_price = float(parts[1])
                    elif price.endswith("-"):
                        min_price = float(parts[0])
                    else:
                        min_price, max_price = map(float, parts)
            except (ValueError, IndexError):
                pass

        # Default sort value
        default_sort_value = "company_id asc"

        # Handling sort_by logic
        sort_by_value = sort_by
        if sort_by == "asc":
            sort_by = "price_sell asc"
        elif sort_by == "dsc":
            sort_by = "price_sell desc"
        else:
            sort_by = default_sort_value

        # Initialize the filter conditions
        
        # Apply keyword filter if present
        if keyword and len(keyword) > 1:
            domain += [
                "|",
                "|",
                "|",
                ("product_id.name", "ilike", keyword),
                ("product_id.description", "ilike", keyword),
                ("product_id.default_code", "ilike", keyword),
                ("product_description", "ilike", keyword),
            ]

        # Apply category filter if present
        if category:
            domain += [("product_id.categ_id", "=", category.id)]

        # Price filter
        if min_price is not None:
            domain.append(("price_sell", ">=", min_price))
        if max_price is not None:
            domain.append(("price_sell", "<=", max_price))

        vendor_product = False
        vendor_settings = False
        if vendor:
            vendor_id_str = vendor.split("-")[-1]
            if vendor_id_str.isdigit():
                vendor_id = int(vendor_id_str)
                domain.append(("company_id", "=", vendor_id))
                vendor_product = request.env["res.company"].sudo().browse(vendor_id)
                # vendor_settings=request.env['ecommerce.main.settings'].sudo().search([('company_id','=',vendor_id)],limit=1)
            else:
                pass

        if v:
            v_id = int(v)
            domain.append(("company_id", "=", v))
            vendor_product = request.env["res.company"].sudo().browse(v_id)
            # vendor_settings=request.env['ecommerce.main.settings'].sudo().search([('company_id','=',vendor_id)],limit=1)
        else:
            pass
        # Attributes
        attribute_variants = request.httprequest.args.getlist("attribute_variants")
        parsed_variants = set()
        for variant in attribute_variants:
            if "-" in variant:
                try:
                    attribute_id, value_id = map(int, variant.split("-"))
                    parsed_variants.add((attribute_id, value_id))
                except ValueError:
                    continue
        if parsed_variants:
            attribute_domain = []
            for attr_id, val_id in parsed_variants:
                attribute_domain.extend(
                    [
                        "&",
                        ("product_attributes_ids.attribute_id", "=", attr_id),
                        ("product_attributes_ids.value_ids", "=", val_id),
                    ]
                )

            if len(parsed_variants) > 1:
                attribute_domain = ["|"] * (len(parsed_variants) - 1) + attribute_domain

            domain += attribute_domain

        # Get the filtered products
        branch_products = branch_products_template.sudo().search(
            domain, order=sort_by, limit=page_size, offset=offset
        )

        # Get the total product count for pagination
        product_count = branch_products_template.sudo().search_count(domain)
        total_pages = math.ceil(product_count / page_size)

        # Prepare the product data
        products_with_custom_pricing = []
        for branch_product in branch_products:
            product = branch_product.product_id
            products_with_custom_pricing.append(
                {
                    "products": product,
                    "custom_product": branch_product,
                    "price": branch_product.price_sell or product.list_price,
                    "attributes": branch_product.saleable_qty or product.description,
                    "branch": branch_product.company_id,
                }
            )

        layout_mode = request.session.get("website_sale_shop_layout_mode", "grid")

        # sort by
        sort_by = self.get_sort_name(sort_by_value)

        response = request.render(
            "base_accounting_kit.ecommerce_products_page",
            {
                "all_attr_products": products_with_custom_pricing,
                "product_categories": product_categories,
                "product_attributes": product_attributes,
                "page_size": page_size,
                "page": page,
                "product_count": product_count,
                "total_pages": total_pages,
                "layout_mode": layout_mode,
                "sort_by": sort_by,
                "keyword": keyword,
                "filter_category": category,
                "min_price": min_price,
                "max_price": max_price,
                "parsed_variants": list(parsed_variants),
                "vendor_product": vendor_product,
                "vendor_settings": vendor_settings,
            },
        )
        return response

    def get_sort_name(self, sort_by):
        sort_by_mapping = {
            "newest": "New arrivals",
            "asc": "Price low to high",
            "dsc": "Price high to low",
        }

        if sort_by in sort_by_mapping:
            return sort_by_mapping[sort_by]
        else:
            return "Best Match"

    @http.route(
        ["/products/searchbar"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def search_product(self, keywords, vendor=None, **kw):

        if keywords is None:
            return {"error": "No search term provided."}

        origin_url = utils.EcomUtils.get_current_origin()
        parent_company = (
            request.env["res.company"]
            .sudo()
            .search([("website", "=", origin_url["origin_url"])], limit=1)
        )

        if origin_url["origin_url"] == ECOMMERCE_MAIN_DOMAIN:
            domain = [
                ("custom_price_ids.publish", "=", True),
                "|",
                "|",
                "|",
                ("name", "ilike", keywords),
                ("description", "ilike", keywords),
                ("default_code", "ilike", keywords),
                ("custom_price_ids.product_description", "ilike", keywords),
            ]
        else:
            domain = [
                ("custom_price_ids.publish", "=", True),
                # "|",
                # ("company_id.parent_id", "=", parent_company.id),
                # ("company_id", "=", parent_company.id),
                "|",
                "|",
                "|",
                ("name", "ilike", keywords),
                ("description", "ilike", keywords),
                ("default_code", "ilike", keywords),
                ("custom_price_ids.product_description", "ilike", keywords),
            ]
        if vendor:
            domain = [
                ("custom_price_ids.publish", "=", True),
                ("custom_price_ids.company_id", "=", vendor),
                "|",
                "|",
                "|",
                ("name", "ilike", keywords),
                ("description", "ilike", keywords),
                ("default_code", "ilike", keywords),
                ("custom_price_ids.product_description", "ilike", keywords),
            ]

        products = (
            request.env["product.template"]
            .sudo()
            .search(
                domain,
                limit=10,
            )
        )
        result = []
        for product in products:
            result.append(
                {
                    "product_name": product.name,
                }
            )

        return {"products": result}
