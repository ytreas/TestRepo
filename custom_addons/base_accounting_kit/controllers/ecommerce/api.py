from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import ValidationError, AccessDenied
from werkzeug.urls import url_parse, url_decode
import ast
from werkzeug.exceptions import NotFound, UnprocessableEntity, BadRequest
import os
from werkzeug.utils import redirect
import hmac
import hashlib
import base64
import uuid
from .utils import SendMail
import json
import requests
from odoo import fields
from collections import defaultdict
from datetime import datetime
import datetime
import nepali_datetime
from .utils import NepalTZ
import jwt as jsonwt
from . import jwt
import math

ECOMMERCE_MAIN_DOMAIN = os.getenv("ECOMMERCE_MAIN_DOMAIN", "http://lekhaplus.com/")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "")
REFRESH_TOKEN_EXPIRY = datetime.timedelta(
    days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRY_days", 30))
)
ACCESS_TOKEN_EXPIRY = datetime.timedelta(
    hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRY_days", 1))
)


class APIMain(http.Controller):

    # GET: /api/v1/products
    @http.route(
        "/api/v1/products",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def products(self):
        try:
            try:
                request_data = request.httprequest.data
                data = json.loads(request_data)
            except (ValueError, TypeError):
                raise BadRequest("Improper json(request body) format.")
            page_size = int(data.get("page_size", 20))
            page = int(data.get("page", 1))
            sort_by = data.get("sort_by", None)
            category_id = data.get("category_id", None)
            vendor_id = data.get("vendor_id", None)
            price = data.get("price", None)
            attribute_variants = data.get("attribute_variants")
            offset = (page - 1) * page_size

            domain = [
                ("publish", "=", True),
                ("saleable_qty", ">", 0),
            ]

            # Price filter
            if price:
                if isinstance(price, dict):
                    if "min_price" in price and "max_price" in price:
                        try:
                            min_price = (
                                float(price["min_price"])
                                if price["min_price"] is not None
                                else None
                            )
                            max_price = (
                                float(price["max_price"])
                                if price["max_price"] is not None
                                else None
                            )
                        except (ValueError, TypeError):
                            raise BadRequest(
                                "Both 'min_price' and 'max_price' must be numeric values."
                            )
                    else:
                        raise BadRequest(
                            "Missing 'min_price' or 'max_price' in price object."
                        )
                else:
                    raise BadRequest(
                        f"Price must be a dictionary, but received {type(price).__name__}"
                    )
            else:
                min_price = max_price = None

            if min_price is not None:
                domain.append(("price_sell", ">=", min_price))
            if max_price is not None:
                domain.append(("price_sell", "<=", max_price))

            # Category filter
            if category_id:
                if not isinstance(category_id, int):
                    raise BadRequest("category_id must be of type integer.")
                else:
                    domain.append(("product_id.categ_id", "=", category_id))

            # Vendor filter
            if vendor_id:
                if not isinstance(vendor_id, int):
                    raise BadRequest("vendor_id must be of type integer.")
                else:
                    domain.append(("company_id.id", "=", vendor_id))

            # product attributes filter
            parsed_variants = set()
            if attribute_variants:
                for variant in attribute_variants:
                    if not isinstance(variant, dict):
                        raise BadRequest(
                            f"Each variant must be a dictionary, but received {type(variant).__name__}"
                        )

                    if "id" not in variant or "value" not in variant:
                        raise BadRequest(
                            "Each variant must contain 'id' and 'value' keys."
                        )

                    value = variant["value"]

                    if not isinstance(value, dict):
                        raise BadRequest(
                            f"'value' must be a dictionary, but received {type(value).__name__}"
                        )

                    if "id" not in value:
                        raise BadRequest("'value' dictionary must contain an 'id' key.")

                    try:
                        attribute_id = int(variant["id"])
                        value_id = int(value["id"])
                    except (ValueError, TypeError):
                        raise BadRequest("'id' values must be valid integers.")

                    parsed_variants.add((attribute_id, value_id))

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
                        attribute_domain = ["|"] * (
                            len(parsed_variants) - 1
                        ) + attribute_domain

                    domain += attribute_domain

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

            branch_products_template = request.env["product.custom.price"]
            branch_products = branch_products_template.sudo().search(
                domain, order=sort_by, limit=page_size, offset=offset
            )
            if not branch_products:
                raise NotFound(_("There are no products matching given criteria."))

            product_count = branch_products_template.sudo().search_count(domain)
            total_pages = math.ceil(product_count / page_size)
            products_with_custom_pricing = []
            for branch_product in branch_products:
                product = branch_product.product_id
                products_with_custom_pricing.append(
                    {
                        "product_id": product.id,
                        "vendor_product_id": branch_product.id,
                        "product_name": product.name,
                        "discount": branch_product.discount,
                        "price_before_discount": self.price_before_discount(
                            branch_product.price_sell, branch_product.discount
                        ),
                        "price_sell": branch_product.price_sell or product.list_price,
                        "rating": {
                            "rating_count": branch_product.rating_count,
                            "rating_avg": branch_product.rating_avg,
                        },
                        "thumbnail_image_uri": self.get_thumbnail_uri(
                            branch_product.id
                        ),
                        "product_url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{product.id}/{branch_product.company_id.id}",
                        "sold_by": {
                            "id": branch_product.company_id.id,
                            "name": branch_product.company_id.name,
                        },
                    }
                )
            sort_by = self.get_sort_name(sort_by_value)

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "products": products_with_custom_pricing,
                            "sort_by": sort_by,
                            "category_id": category_id,
                            "vendor_id": vendor_id,
                            "product_attributes": attribute_variants,
                            "min_price": min_price,
                            "max_price": max_price,
                            "pagination": {
                                "item_count": product_count,
                                "total_pages": total_pages,
                                "page": page,
                                "page_size": page_size,
                            },
                        },
                        "api_for_single_product": "/api/v1/products/1",
                        "api_for_product_categories": "/api/v1/categories",
                        "sort_by_list": "/api/v1/sort-by-list",
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {"success": False, "message": f"{_('Not found')}", "error": str(e)}
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": f"{_('Something went wrong')}",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/products/searchbar
    @http.route(
        "/api/v1/products/searchbar",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def products_searchbar(
        self,
    ):
        try:
            request_data = request.httprequest.data
            data = json.loads(request_data)

            keywords = data.get("keywords")
            if keywords is None:
                raise BadRequest("No keywords provided.")
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

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "result": result,
                        },
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/products/search
    @http.route(
        "/api/v1/products/searchall",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def products_searchall(self):
        try:
            request_data = request.httprequest.data
            data = json.loads(request_data)

            page_size = int(data.get("page_size", 20))
            page = int(data.get("page", 1))
            offset = (page - 1) * page_size
            sort_by = data.get("sort_by", None)

            keywords = data.get("keywords")
            if keywords is None:
                raise BadRequest("No keywords provided.")
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
            domain = [
                ("publish", "=", True),
                ("saleable_qty", ">", 0),
                "|",
                "|",
                "|",
                ("product_id.name", "ilike", keywords),
                ("product_id.description", "ilike", keywords),
                ("product_id.default_code", "ilike", keywords),
                ("product_description", "ilike", keywords),
            ]
            branch_products_template = request.env["product.custom.price"]
            branch_products = branch_products_template.sudo().search(
                domain, order=sort_by, limit=page_size, offset=offset
            )
            if not branch_products:
                raise NotFound(_("There are no products matching given criteria."))

            product_count = branch_products_template.sudo().search_count(domain)
            total_pages = math.ceil(product_count / page_size)
            products_with_custom_pricing = []
            for branch_product in branch_products:
                product = branch_product.product_id
                products_with_custom_pricing.append(
                    {
                        "product_id": product.id,
                        "product_name": product.name,
                        "discount": branch_product.discount,
                        "price_before_discount": self.price_before_discount(
                            branch_product.price_sell, branch_product.discount
                        ),
                        "price_sell": branch_product.price_sell or product.list_price,
                        "rating": {
                            "rating_count": branch_product.rating_count,
                            "rating_avg": branch_product.rating_avg,
                        },
                        "thumbnail_image_uri": self.get_thumbnail_uri(
                            branch_product.id
                        ),
                        "product_url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{product.id}/{branch_product.company_id.id}",
                        "sold_by": {
                            "id": branch_product.company_id.id,
                            "name": branch_product.company_id.name,
                        },
                    }
                )
            sort_by = self.get_sort_name(sort_by_value)

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "products": products_with_custom_pricing,
                            "sort_by": sort_by,
                            "pagination": {
                                "item_count": product_count,
                                "total_pages": total_pages,
                                "page": page,
                                "page_size": page_size,
                            },
                        },
                        "api_for_single_product": "/api/v1/products/1",
                        "api_for_product_categories": "/api/v1/categories",
                        "sort_by_list": "/api/v1/sort-by-list",
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/categories
    @http.route(
        "/api/v1/categories",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def categories(
        self,
        page=1,
        page_size=20,
        sort_by=None,
    ):
        try:
            page_size = int(page_size)
            page = int(page)
            offset = (page - 1) * page_size
            sort_by_value = sort_by
            if sort_by == "asc":
                sort_by = "name asc"
            elif sort_by == "dsc":
                sort_by = "name desc"
            else:
                sort_by = None

            parent_company = (
                request.env["res.company"]
                .sudo()
                .search([("website", "=", ECOMMERCE_MAIN_DOMAIN)], limit=1)
            )
            domain = [("company_id", "=", parent_company.id)]
            product_categories = (
                request.env["product.category"]
                .sudo()
                .search(domain, order=sort_by, limit=page_size, offset=offset)
            )
            categories_count = product_categories.sudo().search_count(domain)
            total_pages = math.ceil(categories_count / page_size)

            categories = []

            for cat in product_categories:
                categories.append(
                    {
                        "id": cat.id,
                        "name": cat.name,
                        "product_count": self.get_category_product_count(cat.id),
                        "products": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/categories/{cat.id}",
                    }
                )

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "categories": categories,
                            "sort_by": self.get_sort_category_name(sort_by_value),
                            "pagination": {
                                "item_count": categories_count,
                                "total_pages": total_pages,
                                "page": page,
                                "page_size": page_size,
                            },
                        },
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Oopsss…Something went wrong!!"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/attributes
    @http.route(
        "/api/v1/product-attributes",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def product_attributes(
        self,
        page=1,
        page_size=20,
        sort_by=None,
    ):
        try:
            page_size = int(page_size)
            page = int(page)
            offset = (page - 1) * page_size
            if sort_by == "asc":
                sort_by = "name asc"
            elif sort_by == "dsc":
                sort_by = "name desc"
            else:
                sort_by = None

            parent_company = (
                request.env["res.company"]
                .sudo()
                .search([("website", "=", ECOMMERCE_MAIN_DOMAIN)], limit=1)
            )
            domain = [("company_id", "=", parent_company.id)]
            product_attributes = (
                request.env["cp.attribute"]
                .sudo()
                .search(domain, order=sort_by, limit=page_size, offset=offset)
            )
            attributes_count = product_attributes.sudo().search_count(domain)
            total_pages = math.ceil(attributes_count / page_size)

            attributes = []

            for attr in product_attributes:
                vals = []
                for atr in attr.value_ids:
                    vals.append(
                        {
                            "id": atr.id,
                            "name": atr.name,
                        }
                    )
                attributes.append(
                    {
                        "id": attr.id,
                        "name": _(f"{attr.name}"),
                        "value": vals,
                    }
                )

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "attributes": attributes,
                            "pagination": {
                                "item_count": attributes_count,
                                "total_pages": total_pages,
                                "page": page,
                                "page_size": page_size,
                            },
                        },
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Oopsss…Something went wrong!!"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/categories/123
    @http.route(
        "/api/v1/categories/<int:category_id>",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def category_products(
        self,
        page=1,
        page_size=20,
        sort_by=None,
        category_id=None,
    ):
        try:
            if category_id is None or not isinstance(category_id, int):
                raise BadRequest(_("Bad Request"))

            category = request.env["product.category"].sudo().browse(category_id)
            if not category:
                raise NotFound(_("Given category is not available."))

            page_size = int(page_size)
            page = int(page)
            offset = (page - 1) * page_size
            domain = [
                ("publish", "=", True),
                ("saleable_qty", ">", 0),
                ("product_id.categ_id.id", "=", int(category_id)),
            ]
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

            branch_products_template = request.env["product.custom.price"]
            branch_products = branch_products_template.sudo().search(
                domain, order=sort_by, limit=page_size, offset=offset
            )
            if not branch_products:
                raise NotFound(_("There are no products matching given criteria."))

            product_count = branch_products_template.sudo().search_count(domain)
            total_pages = math.ceil(product_count / page_size)
            products_with_custom_pricing = []
            for branch_product in branch_products:
                product = branch_product.product_id
                products_with_custom_pricing.append(
                    {
                        "product_id": product.id,
                        "product_name": product.name,
                        "discount": branch_product.discount,
                        "price_before_discount": self.price_before_discount(
                            branch_product.price_sell, branch_product.discount
                        ),
                        "price_sell": branch_product.price_sell or product.list_price,
                        "url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{product.id}/{branch_product.company_id.id}",
                        "rating": {
                            "rating_count": branch_product.rating_count,
                            "rating_avg": branch_product.rating_avg,
                        },
                        "thumbnail_image_uri": self.get_thumbnail_uri(
                            branch_product.id
                        ),
                        "sold_by": {
                            "id": branch_product.company_id.id,
                            "name": branch_product.company_id.name,
                        },
                    }
                )
            sort_by = self.get_sort_name(sort_by_value)

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "products": products_with_custom_pricing,
                            "sort_by": sort_by,
                            "pagination": {
                                "item_count": product_count,
                                "total_pages": total_pages,
                                "page": page,
                                "page_size": page_size,
                            },
                        },
                        "api_for_single_product": "/api/v1/products/1",
                        "api_for_product_categories": "/api/v1/categories",
                        "sort_by_list": "/api/v1/sort-by-list",
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {"success": False, "message": f"{_('Not found')}", "error": str(e)}
                ),
                content_type="application/json",
                status=404,
            )
        except BadRequest as e:
            return Response(
                json.dumps({"success": False, "message": str(e)}),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": f"{_('Something went wrong')}",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/products/product-123/vendor-345
    @http.route(
        "/api/v1/products/<int:product_id>/<int:sold_by_id>",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def product(self, product_id=None, sold_by_id=None):
        try:
            if product_id is None or not isinstance(product_id, int):
                raise BadRequest(_("Product id is required and it must be an integer"))

            if sold_by_id is None or not isinstance(sold_by_id, int):
                raise BadRequest(_("Vendor id is required and it must be an integer"))

            product = self.get_product(product_id)
            vendor = self.get_vendor(sold_by_id)

            if not product:
                raise NotFound(_("Product not found"))
            if not vendor:
                raise NotFound(_("Vendor not found"))

            main_product = self.get_main_product(product_id, sold_by_id)
            if not main_product:
                raise NotFound(_("Product associated with given vendor not found"))

            product = {
                "id": main_product.product_id.id,
                "vendor_product_id": main_product.id,
                "name": main_product.product_id.name,
                "discount": main_product.discount,
                "price_before_discount": self.price_before_discount(
                    main_product.price_sell, main_product.discount
                ),
                "price_sell": main_product.price_sell or 999,
                "in_stock_quantity": main_product.saleable_qty,
                "min_quantity": main_product.min_qty,
                "max_quantity": main_product.max_qty,
                "attributes": self.get_product_attributes(main_product),
                "thumbnail_image_uri": self.get_thumbnail_uri(main_product.id),
                "description": main_product.product_description or main_product.product_id.description or '--No description for this product--',
                "featured_image_uri": self.get_featured_images(main_product.id, 512),
                "rating": {
                    "rating_count": main_product.rating_count,
                    "rating_avg": main_product.rating_avg,
                    "product_reviews": self.get_product_reviews(main_product.id),
                },
                "wishlist_count": request.env["ecommerce.wishlist"].wishlist_count(
                    main_product.id
                ),
                "recommended_products": self.get_recommended_products(main_product),
                "sold_by": {
                    "id": main_product.company_id.id,
                    "name": main_product.company_id.name,
                    "logo_url": f"{ECOMMERCE_MAIN_DOMAIN}web/image?model=res.company&id={main_product.company_id.id}&field=logo",
                    "vendor_details_url": f"{ECOMMERCE_MAIN_DOMAIN}/api/v1/vendor-details/{main_product.company_id.id}",
                },
            }

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": product,
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {"success": False, "message": f"{_('Not found')}", "error": str(e)}
                ),
                content_type="application/json",
                status=404,
            )
        except BadRequest as e:
            return Response(
                json.dumps({"success": False, "message": str(e)}),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": f"{_('Something went wrong')}",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/login
    @http.route(
        "/api/v1/login",
        type="http",
        auth="public",
        csrf=False,
        cors="*",
        methods=["POST"],
    )
    def login(self, **kw):

        raw_data = request.httprequest.data
        json_data = json.loads(raw_data)

        email = json_data.get("email")
        password = json_data.get("password")

        try:
            uid = request.session.authenticate(
                request.db or "res.users", email, password
            )
            if uid:
                user = request.env["res.users"].sudo().browse(uid)

                # Generate access token
                access_payload = {
                    "user_id": user.id,
                    "exp": datetime.datetime.now(datetime.timezone.utc)
                    + ACCESS_TOKEN_EXPIRY,
                    "email": email,
                    "password": password,
                    "company_id": user.company_id.id,
                }
                access_token = jsonwt.encode(
                    access_payload, SECRET_KEY, algorithm="HS256"
                )

                # Generate refresh token
                refresh_payload = {
                    "user_id": user.id,
                    "exp": datetime.datetime.now(datetime.timezone.utc)
                    + REFRESH_TOKEN_EXPIRY,
                }
                refresh_token = jsonwt.encode(
                    refresh_payload, REFRESH_SECRET_KEY, algorithm="HS256"
                )

                return Response(
                    json.dumps(
                        {
                            "success": True,
                            "data": {
                                "access_token": access_token,
                                "refresh_token": refresh_token,
                            },
                        }
                    ),
                    content_type="application/json",
                    status=200,
                )
            else:
                raise AccessDenied(_("Login credential did not match!"))

        except AccessDenied as e:
            return Response(
                json.dumps({"success": False, "message": str(e)}),
                content_type="application/json",
                status=401,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Something went wrong!"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/my-cart
    @http.route(
        "/api/v1/my-cart",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def my_cart(
        self,
        page=1,
        page_size=20,
        sort_by=None,
        category_id=None,
    ):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            page_size = int(page_size)
            page = int(page)
            offset = (page - 1) * page_size

            my_cart = (
                request.env["ecommerce.add.to.cart"].sudo().get_my_cart(user_id=user_id)
            )
            cart_list = []
            for c in my_cart:
                cart_list.append(
                    {
                        "id": c.id,
                        "product_id": c.product_id.product_id.id,
                        "vendor_product_id": c.product_id.id,
                        "product_name": c.product_id.product_id.name,
                        "product_status": c.product_id.saleable_qty > 0,
                        "per_unit_price": c.price_unit,
                        "product_url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{c.product_id.product_id.id}/{c.product_id.company_id.id}",
                        "quantity": c.quantity,
                        "attributes": self.get_cart_product_attributes(c.id),
                    }
                )
            cart_quantity = request.env["website"].sudo().get_cart_quantity(user_id)
            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {"cart": cart_list, "quantity": cart_quantity},
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Something went wrong"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/add-to-cart
    @http.route(
        "/api/v1/add-to-cart",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def add_to_cart(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            request_data = request.httprequest.data
            data = json.loads(request_data)
            product_id = int(data.get("product_id", 0))
            qty = int(data.get("quantity", 1))
            attributes = data.get("attributes", [])
            unit_price = float(data.get("unit_price", 0.0))
            user_id = auth_status["user_id"]
            if (
                product_id is None
                or qty is None
                or unit_price is None
                or not isinstance(product_id, int)
                or not isinstance(qty, int)
                or not isinstance(unit_price, float)
            ):
                raise BadRequest(
                    _(
                        "product_id(integer), quantity(integer), unit_price(float) are required!"
                    )
                )
            product = request.env["product.custom.price"].sudo().browse(product_id)
            if not product:
                raise BadRequest(_("Invalid product ID"))
            attributes_list = []
            for attr in attributes:
                value = attr["value"][0]
                attributes_list.append((int(attr["id"]), int(value["id"])))
            cart = (
                request.env["ecommerce.add.to.cart"]
                .sudo()
                .search(
                    [
                        ("user_id", "=", user_id),
                        ("product_id", "=", product_id),
                        ("status", "in", ["active"]),
                    ]
                )
            )
            cart_with_attributes = None
            for cart_item in cart:
                cart_item_attributes = [
                    (attr.attribute_id.id, attr.value_id.id)
                    for attr in cart_item.cart_attribute_ids
                ]

                if sorted(cart_item_attributes) == sorted(attributes_list):
                    cart_with_attributes = cart_item
                    break
            if cart_with_attributes:
                cart_quantity = cart_with_attributes.quantity + qty
                cart_with_attributes.write({"quantity": cart_quantity})
                cart_id = cart_with_attributes.id
            else:
                cart = (
                    request.env["ecommerce.add.to.cart"]
                    .sudo()
                    .create(
                        {
                            "user_id": user_id,
                            "product_id": product_id,
                            "quantity": qty,
                            "price_unit": unit_price,
                        }
                    )
                )
                cart_id = cart.id
                for attr in attributes_list:
                    attribute_id, value_id = attr
                    attribute = (
                        request.env["cp.attribute"]
                        .sudo()
                        .search([("id", "=", attribute_id)])
                    )
                    value = (
                        request.env["cp.attribute.value"]
                        .sudo()
                        .search([("id", "=", value_id)])
                    )

                    if not attribute or not value:
                        raise BadRequest(
                            f"Invalid attribute or value for {attribute_id}-{value_id}"
                        )

                    request.env["ecommerce.cart.attributes"].sudo().create(
                        {
                            "cart_id": cart.id,
                            "attribute_id": attribute_id,
                            "value_id": value_id,
                        }
                    )
            cart_quantity = request.env["website"].sudo().get_cart_quantity(user_id)
            individual_quantity = self.get_individual_cart_quantity(cart_id, user_id)

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "cart": {
                                "id": cart_id,
                                "quantity_in_cart_current_item": individual_quantity,
                                "url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/my-cart/{cart_id}",
                            },
                            "product": {
                                "id": product.product_id.id,
                                "name": product.product_id.name,
                                "url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{product.product_id.id}/{product.company_id.id}",
                            },
                            "total_item": cart.search_count([]),
                            "total_quantity": cart_quantity,
                        },
                        "view_my_cart": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/my-cart",
                    }
                ),
                content_type="application/json",
                status=201,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Bad Request"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Something went wrong"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/update-cart
    @http.route(
        "/api/v1/update-cart",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def update_cart(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            request_data = request.httprequest.data
            data = json.loads(request_data)
            cart_id = int(data.get("cart_id", 0))
            qty = int(data.get("quantity", 1))
            if (
                cart_id is None
                or qty is None
                or not isinstance(cart_id, int)
                or not isinstance(qty, int)
            ):
                raise BadRequest(
                    _("cart_id and quantity are required and must me of type integer.")
                )
            my_cart = (
                request.env["ecommerce.add.to.cart"]
                .sudo()
                .search(
                    [
                        ("id", "=", cart_id),
                        ("user_id", "=", user_id),
                    ]
                )
            )
            if not my_cart:
                raise NotFound("Cart not found")

            my_cart.sudo().write(
                {
                    "quantity": qty,
                }
            )
            cart_quantity = request.env["website"].sudo().get_cart_quantity(user_id)
            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {"cart_id": cart_id, "quantity": cart_quantity},
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/unlink-cart
    @http.route(
        "/api/v1/unlink-cart",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def unlink_cart(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            request_data = request.httprequest.data
            data = json.loads(request_data)
            cart_id = int(data.get("cart_id"))
            if cart_id is None or not isinstance(cart_id, int):
                raise BadRequest(_("cart_id is required and must me of type integer."))
            my_cart = (
                request.env["ecommerce.add.to.cart"]
                .sudo()
                .search(
                    [
                        ("id", "=", cart_id),
                        ("user_id", "=", user_id),
                    ]
                )
            )
            if not my_cart:
                raise NotFound("Cart not found")
            my_cart.unlink()
            cart_quantity = request.env["website"].sudo().get_cart_quantity(user_id)
            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {"cart_id": cart_id, "quantity": cart_quantity},
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/my-wishlist
    @http.route(
        "/api/v1/my-wishlist",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def my_wishlist(
        self,
        page=1,
        page_size=20,
        sort_by=None,
        category_id=None,
    ):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            page_size = int(page_size)
            page = int(page)
            offset = (page - 1) * page_size
            my_wishlist = (
                request.env["ecommerce.wishlist"].sudo().get_wishlist_record(user_id)
            )
            wishlist = []
            for w in my_wishlist:
                wishlist.append(
                    {
                        "id": w.id,
                        "product_id": w.product_id.product_id.id,
                        "vendor_id": w.product_id.company_id.id,
                        "vendor_product_id": w.product_id.id,
                        "product_name": w.product_id.product_id.name,
                        "product_status": w.product_id.saleable_qty > 0,
                        "per_unit_price": w.product_id.price_sell,
                        "thumbnail":self.get_thumbnail_uri(w.product_id.id),
                        "product_url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{w.product_id.product_id.id}/{w.product_id.company_id.id}",
                        "attributes": self.get_wishlist_product_attributes(w.id),
                    }
                )
            wishlist_count = my_wishlist.search_count(
                [
                    ("user_id", "=", user_id),
                ]
            )

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {"wishlist": wishlist, "quantity": wishlist_count},
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/add-to-wishlist
    @http.route(
        "/api/v1/add-to-wishlist",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def add_to_wishlist(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            request_data = request.httprequest.data
            data = json.loads(request_data)
            product_id = int(data.get("product_id", 0))
            attributes = data.get("attributes", [])
            if product_id is None or not isinstance(product_id, int):
                raise BadRequest(
                    _("product_id is required and it must be of type integer.")
                )
            product = request.env["product.custom.price"].sudo().browse(product_id)
            if not product:
                raise BadRequest(_("Invalid product ID"))
            attributes_list = []
            for attr in attributes:
                value = attr["value"][0]
                attributes_list.append((int(attr["id"]), int(value["id"])))
            wishlist = (
                request.env["ecommerce.wishlist"]
                .sudo()
                .search(
                    [
                        ("user_id", "=", user_id),
                        ("product_id", "=", product_id),
                    ]
                )
            )
            wishlist_with_attributes = None
            for w in wishlist:
                cart_item_attributes = [
                    (attr.attribute_id.id, attr.value_id.id)
                    for attr in w.wishlist_attribute_ids
                ]

                if sorted(cart_item_attributes) == sorted(attributes_list):
                    wishlist_with_attributes = w
                    break
            if wishlist_with_attributes:
                return Response(
                    json.dumps(
                        {
                            "success": False,
                            "message": _(
                                "Wishlist with the same attributes already exists."
                            ),
                        }
                    ),
                    content_type="application/json",
                    status=409,
                )
            else:
                wishlist = (
                    request.env["ecommerce.wishlist"]
                    .sudo()
                    .create(
                        {
                            "user_id": user_id,
                            "product_id": product_id,
                        }
                    )
                )
                wishlist_id = wishlist.id
                for attr in attributes_list:
                    attribute_id, value_id = attr
                    attribute = (
                        request.env["cp.attribute"]
                        .sudo()
                        .search([("id", "=", attribute_id)])
                    )
                    value = (
                        request.env["cp.attribute.value"]
                        .sudo()
                        .search([("id", "=", value_id)])
                    )

                    if not attribute or not value:
                        raise BadRequest(
                            f"Invalid attribute or value for {attribute_id}-{value_id}"
                        )

                    request.env["ecommerce.wishlist.attributes"].sudo().create(
                        {
                            "wishlist_id": wishlist.id,
                            "attribute_id": attribute_id,
                            "value_id": value_id,
                        }
                    )
            wishlist_quantity = (
                request.env["ecommerce.wishlist"]
                .sudo()
                .search_count([("user_id", "=", user_id)])
            )
            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "wishlist": {
                                "id": wishlist_id,
                                "attributes": self.get_wishlist_product_attributes(
                                    wishlist_id
                                ),
                            },
                            "total_count": wishlist_quantity,
                            "product_url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{product.product_id.id}/{product.company_id.id}",
                        },
                    }
                ),
                content_type="application/json",
                status=201,
            )

        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Bad Request"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Something went wrong"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/unlink-wishlist
    @http.route(
        "/api/v1/unlink-wishlist",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def unlink_wishlist(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            request_data = request.httprequest.data
            data = json.loads(request_data)
            wishlist_id = int(data.get("wishlist_id"))
            if wishlist_id is None or not isinstance(wishlist_id, int):
                raise BadRequest(
                    _("wishlist_id is required and must me of type integer.")
                )
            wishlist = (
                request.env["ecommerce.wishlist"]
                .sudo()
                .search(
                    [
                        ("id", "=", wishlist_id),
                        ("user_id", "=", user_id),
                    ]
                )
            )
            if not wishlist:
                raise NotFound("Wishlist not found")
            wishlist.unlink()
            wishlist_quantity = wishlist.search_count(
                [
                    ("user_id", "=", user_id),
                ]
            )
            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "wishlist_id": wishlist_id,
                            "quantity": wishlist_quantity,
                        },
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/address
    @http.route(
        "/api/v1/address/<string:address_type>",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def address(self, address_type):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )

            if not address_type or address_type not in ["delivery", "invoice", "all"]:
                raise BadRequest(
                    _(
                        "address_type is required and it can be delivery or invoice or all."
                    )
                )
            user_id = auth_status["user_id"]
            master_address = request.env["res.partner"].sudo()

            address = []
            user = request.env["res.users"].sudo().browse(user_id)
            if address_type != "all":
                master_address = master_address.get_addresses(
                    user.commercial_partner_id.id, address_type
                )
                for a in master_address:
                    address.append(
                        {
                            "id": a.id,
                            "address_type": a.type,
                            "name": a.name,
                            "user_id": user_id,
                            "complete_name": f"{a.complete_name}",
                            "type": a.type,
                            "default_address": a.address_selected,
                            "street": a.street,
                            "street2": a.street2,
                            "email": a.email,
                            "mobile": a.mobile,
                            "active": a.active,
                            "partner_latitude": a.partner_latitude,
                            "partner_longitude": a.partner_longitude,
                        }
                    )
            else:
                for a in master_address.search(
                    [
                        ("commercial_partner_id", "=", user.commercial_partner_id.id),
                        ("type", "in", ["delivery", "invoice"]),
                    ]
                ):
                    address.append(
                        {
                            "id": a.id,
                            "address_type": a.type,
                            "name": a.name,
                            "user_id": user_id,
                            "complete_name": f"{a.complete_name}",
                            "type": a.type,
                            "default_address": a.address_selected,
                            "street": a.street,
                            "street2": a.street2,
                            "email": a.email,
                            "mobile": a.mobile,
                            "active": a.active,
                            "partner_latitude": a.partner_latitude,
                            "partner_longitude": a.partner_longitude,
                        }
                    )

            return Response(
                json.dumps({"success": True, "data": {"address": address}}),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Bad Request"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Something went wrong"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST:/api/v1/address
    @http.route(
        "/api/v1/address",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def add_address(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            user = request.env["res.users"].sudo().browse(user_id)
            request_data = request.httprequest.data
            data = json.loads(request_data)

            fullname = data.get("fullname")
            if (
                fullname is None
                or not isinstance(fullname, str)
                or not fullname.strip()
            ):
                raise BadRequest(
                    _("Fullname is required and must be a non-empty string.")
                )

            phone = data.get("phone")
            if phone is None or not isinstance(phone, str) or not phone.strip():
                raise BadRequest(_("Phone must be a non-empty string."))

            email = data.get("email")
            if email is None or (not isinstance(email, str) or "@" not in email):
                raise BadRequest(
                    _("Email is required and it must be valid email format.")
                )

            street = data.get("street")
            if street is None or not isinstance(street, str):
                raise BadRequest(_("street is required and it must be a string."))

            address = data.get("address")
            if address is None or not isinstance(address, str):
                raise BadRequest(_("Address is required and it must be a string."))

            type = data.get("type")
            if type is None or type not in ["delivery", "invoice"]:
                raise BadRequest(
                    _("Invalid type. It must be either 'delivery' or 'invoice'.")
                )

            latitude = data.get("latitude", None)
            if latitude is None:
                raise BadRequest(_("latitude is required."))
            if latitude is not None:
                try:
                    latitude = float(latitude)
                    if not (-90 <= latitude <= 90):
                        raise ValueError
                except ValueError:
                    raise BadRequest(
                        _(
                            "Latitude is required and must be a number between -90 and 90."
                        )
                    )

            longitude = data.get("longitude", None)
            if longitude is None:
                raise BadRequest(_("longitude is required."))

            if longitude is None or longitude is not None:
                try:
                    longitude = float(longitude)
                    if not (-180 <= longitude <= 180):
                        raise ValueError
                except ValueError:
                    raise BadRequest(
                        _(
                            "Longitude is required and must be a number between -180 and 180."
                        )
                    )
            master_address = (
                request.env["res.partner"]
                .sudo()
                .get_addresses(user.commercial_partner_id.id, type)
            )
            if type == "invoice" and master_address.search_count([]) > 1:
                raise BadRequest(
                    _(
                        "Invoice address already exists for the provided user. Please either update or delete and create a new."
                    )
                )

            address_vals = {
                "commercial_partner_id": user.commercial_partner_id.id,
                "name": fullname,
                "parent_id": user.commercial_partner_id.id,
                "user_id": user.id,
                "complete_name": f"{user.name}, {fullname}",
                "type": type,
                "street": address,
                "street2": street,
                "email": email,
                "mobile": phone,
                "active": True,
                "partner_latitude": latitude,
                "partner_longitude": longitude,
            }
            new_address = request.env["res.partner"].sudo().create(address_vals)

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "address": {
                                "id": new_address.id,
                                "fullname": new_address.complete_name,
                                "type": new_address.type,
                                "email": new_address.email,
                                "address": new_address.street,
                                "street": new_address.street2,
                                "mobile": new_address.mobile,
                                "status": new_address.active,
                                "latitude": new_address.partner_latitude,
                                "longitude": new_address.partner_longitude,
                            }
                        },
                    }
                ),
                content_type="application/json",
                status=201,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Bad Request"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Something went wrong"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/update-cart
    @http.route(
        "/api/v1/change-delivery-address",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def change_delivery_address(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            user = self.get_user_by_id(user_id)
            if not user:
                raise NotFound("User not found.")
            request_data = request.httprequest.data
            data = json.loads(request_data)
            address_id = data.get("address_id")
            if address_id is None or not isinstance(address_id, int):
                raise BadRequest(
                    _("address_id is required and must me of type integer.")
                )
            address = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [
                        ("commercial_partner_id", "=", user.commercial_partner_id.id),
                        ("id", "=", address_id),
                    ]
                )
            )

            if not address:
                raise NotFound(f"Address with id {address_id} is not found.")

            selected_address = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [
                        ("address_selected", "=", True),
                        (
                            "commercial_partner_id",
                            "=",
                            user.commercial_partner_id.id,
                        ),
                    ]
                )
            )
            selected_address.sudo().write({"address_selected": False})
            address.sudo().write(
                {
                    "address_selected": True,
                }
            )
            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "id": address.id,
                            "address_type": address.type,
                            "name": address.name,
                            "user_id": user_id,
                            "complete_name": f"{address.complete_name}",
                            "type": address.type,
                            "default_address": address.address_selected,
                            "street": address.street,
                            "street2": address.street2,
                            "email": address.email,
                            "mobile": address.mobile,
                            "active": address.active,
                            "partner_latitude": address.partner_latitude,
                            "partner_longitude": address.partner_longitude,
                        },
                    }
                )
            )

        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/update-cart
    @http.route(
        "/api/v1/update-address",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def update_address(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            request_data = request.httprequest.data
            data = json.loads(request_data)
            address_id = data.get("id")
            if address_id is None or not isinstance(address_id, int):
                raise BadRequest("id is required and it must be of type integer.")
            fullname = data.get("fullname")
            if (
                fullname is None
                or not isinstance(fullname, str)
                or not fullname.strip()
            ):
                raise BadRequest(
                    _("Fullname is required and must be a non-empty string.")
                )

            phone = data.get("phone")
            if phone is None or not isinstance(phone, str) or not phone.strip():
                raise BadRequest(_("Phone must be a non-empty string."))

            email = data.get("email")
            if email is None or (not isinstance(email, str) or "@" not in email):
                raise BadRequest(
                    _("Email is required and it must be valid email format.")
                )

            street = data.get("street")
            if street is None or not isinstance(street, str):
                raise BadRequest(_("street is required and it must be a string."))

            address = data.get("address")
            if address is None or not isinstance(address, str):
                raise BadRequest(_("Address is required and it must be a string."))

            type = data.get("type")
            if type is None or type not in ["delivery", "invoice"]:
                raise BadRequest(
                    _("Invalid type. It must be either 'delivery' or 'invoice'.")
                )

            latitude = data.get("latitude", None)
            if latitude is None:
                raise BadRequest(_("latitude is required."))
            if latitude is not None:
                try:
                    latitude = float(latitude)
                    if not (-90 <= latitude <= 90):
                        raise ValueError
                except ValueError:
                    raise BadRequest(
                        _(
                            "Latitude is required and must be a number between -90 and 90."
                        )
                    )

            longitude = data.get("longitude", None)
            if longitude is None:
                raise BadRequest(_("longitude is required."))

            if longitude is None or longitude is not None:
                try:
                    longitude = float(longitude)
                    if not (-180 <= longitude <= 180):
                        raise ValueError
                except ValueError:
                    raise BadRequest(
                        _(
                            "Longitude is required and must be a number between -180 and 180."
                        )
                    )
            user = self.get_user_by_id(user_id)
            if not user:
                raise BadRequest("User does not exist.")
            address_vals = {
                "commercial_partner_id": user.commercial_partner_id.id,
                "name": fullname,
                "parent_id": user.commercial_partner_id.id,
                "user_id": user.id,
                "complete_name": f"{user.name}, {fullname}",
                "type": type,
                "street": address,
                "street2": street,
                "email": email,
                "mobile": phone,
                "active": True,
                "partner_latitude": latitude,
                "partner_longitude": longitude,
            }
            master_address = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [
                        ("id", "=", address_id),
                        ("commercial_partner_id", "=", user.commercial_partner_id.id),
                    ]
                )
            )
            if not master_address:
                raise BadRequest(_("Invalid id provided."))

            master_address.write(address_vals)
            return Response(
                json.dumps({"success": True, "data": {"address": address_vals}}),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/unlink-address
    @http.route(
        "/api/v1/unlink-address",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def unlink_address(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            user = request.env["res.users"].sudo().browse(user_id)
            request_data = request.httprequest.data
            data = json.loads(request_data)
            address_id = int(data.get("id"))
            if address_id is None or not isinstance(address_id, int):
                raise BadRequest(
                    _("address_id is required and must me of type integer.")
                )

            address = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [
                        ("commercial_partner_id", "=", user.commercial_partner_id.id),
                        ("id", "=", address_id),
                    ]
                )
            )
            if not address:
                raise NotFound(f"Address with id {address_id} is not found.")

            address.unlink()
            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "address_id": address_id,
                        },
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/vendor-configurations
    @http.route(
        "/api/v1/vendor-configurations/<int:vendor_id>",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def vendor_configurations(self, vendor_id):
        try:
            if vendor_id is None or not isinstance(vendor_id, int):
                raise BadRequest("vendor_id is required and must be an integer.")

            company = request.env["res.company"].sudo().browse(vendor_id)
            if not company.exists():
                raise NotFound("Vendor not found.")

            company_config = (
                request.env["ecommerce.main.settings"]
                .sudo()
                .search([("company_id", "=", vendor_id)], limit=1, order="id desc")
            )
            if not company_config:
                body = {
                    "enable_delivery_charge": False,
                    "enable_voucher": False,
                    "voucher_code": "",
                }
            else:
                body = {
                    "enable_delivery_charge": company_config.enable_delivery_charge,
                    "enable_voucher": company_config.enable_voucher,
                    "voucher_code": company_config.voucher_code,
                }

            return Response(
                json.dumps({"success": True, "data": body}),
                content_type="application/json",
                status=200,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Not Found"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Bad Request"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Something went wrong"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/vendor-details/<int:vendor_id>
    @http.route(
        "/api/v1/vendor-details/<int:vendor_id>",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def vendor_details(self, vendor_id):
        try:
            if vendor_id is None or not isinstance(vendor_id, int):
                raise BadRequest("vendor_id is required and must be an integer.")

            company = request.env["res.company"].sudo().browse(vendor_id)
            if not company.exists():
                raise NotFound("Vendor not found.")

            details = {
                "name_en": company.name,
                "name_ne": company.name_np,
                "address": company.street_np,
                "registration_no": company.registration_no,
                "pan": company.pan_number,
                "start_date": company.start_date,
                "logo_uri": f"{ECOMMERCE_MAIN_DOMAIN}web/image?model=res.company&id={vendor_id}&field=logo",
            }
            return Response(
                json.dumps({"success": True, "data": details}),
                content_type="application/json",
                status=200,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Not Found"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Bad Request"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Something went wrong"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/delivery-options/<vendor_id>
    @http.route(
        "/api/v1/delivery-charge",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def delivery_charges(self):
        try:
            request_data = request.httprequest.data
            data = json.loads(request_data)
            vendor_id = data.get("vendor_id")
            if vendor_id is None or not isinstance(vendor_id, int):
                raise BadRequest("vendor_id is required and must be an integer.")

            user_id = data.get("user_id")
            user = self.get_user_by_id(user_id)
            if user_id is None or not isinstance(user_id, int):
                raise BadRequest("user_id is required and must be an integer.")
            if not user:
                raise NotFound("user does not exists.")

            default_delivery_location = (
                request.env["res.partner"]
                .sudo()
                .get_default_address("shipping", user.commercial_partner_id.id)
            )
            delivery_charge = (
                request.env["ecommerce.delivery.charges"]
                .sudo()
                .get_delivery_charge(
                    vendor_id,
                    default_delivery_location.partner_latitude,
                    default_delivery_location.partner_longitude,
                )
            )

            company = request.env["res.company"].sudo().browse(vendor_id)
            if not company.exists():
                raise NotFound("Vendor not found.")

            return Response(
                json.dumps(
                    {"success": True, "data": {"delivery_charge": delivery_charge}}
                ),
                content_type="application/json",
                status=200,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Not Found"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Bad Request"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Something went wrong"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/payment-methods/
    @http.route(
        "/api/v1/payment-methods",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def payment_methods(self):
        try:
            allowed_payment_methods = (
                request.env["ecommerce.payment.methods"].sudo().get_allowed_methods()
            )

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {"payment_methods": allowed_payment_methods},
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/payment-methods/
    @http.route(
        "/api/v1/payment-methods-extra-fees",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def payment_methods_extra_fees(self):
        try:
            request_data = request.httprequest.data
            data = json.loads(request_data)
            type = data.get("payment_method_code", "cod")
            allowed_payment_methods = (
                request.env["ecommerce.payment.methods"].sudo().get_allowed_methods()
            )
            if type not in allowed_payment_methods:
                raise BadRequest("Invalid payment method code.")
            extra_charge = (
                request.env["ecommerce.payment.charges"]
                .sudo()
                .search([("fee", ">", 0), ("payment_method.code", "=", type)])
            )
            total_extra_price = 0
            extra_charges_title_list = []
            for ec in extra_charge:
                extra_charges_title_list.append(
                    {
                        "title": ec.title,
                        "charge": ec.fee,
                    }
                )
                total_extra_price += ec.fee

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {
                            "extra_fees": extra_charges_title_list,
                            "total_extra_fees": total_extra_price,
                        },
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/my-orders
    @http.route(
        "/api/v1/my-orders",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def my_orders(
        self,
        page=1,
        page_size=20,
        sort_by=None,
        category_id=None,
    ):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            page_size = int(page_size)
            page = int(page)
            offset = (page - 1) * page_size
            my_wishlist = (
                request.env["ecommerce.wishlist"].sudo().get_wishlist_record(user_id)
            )
            wishlist = []
            for w in my_wishlist:
                wishlist.append(
                    {
                        "id": w.id,
                        "product_id": w.product_id.product_id.id,
                        "vendor_id": w.product_id.company_id.id,
                        "vendor_product_id": w.product_id.id,
                        "product_name": w.product_id.product_id.name,
                        "product_status": w.product_id.saleable_qty > 0,
                        "per_unit_price": w.product_id.price_sell,
                        "product_url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{w.product_id.product_id.id}/{w.product_id.company_id.id}",
                        "attributes": self.get_wishlist_product_attributes(w.id),
                    }
                )
            wishlist_count = my_wishlist.search_count(
                [
                    ("user_id", "=", user_id),
                ]
            )

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {"wishlist": wishlist, "quantity": wishlist_count},
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/product/review
    @http.route(
        "/api/v1/product/review",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def product_review(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            request_data = request.httprequest.data
            data = json.loads(request_data)
            user_id = auth_status["user_id"]
            rating_float = data.get("rating_float", 1)
            rating_comment = data.get("rating_comment", "")
            rating_product = data.get("rating_product")

            if not rating_float or not isinstance(rating_float, float):
                raise BadRequest("rating_float is required and must be a float value.")

            if not (0 <= rating_float <= 5):
                raise BadRequest("rating_float must be between 0 and 5")

            if not rating_product or not isinstance(rating_product, int):
                raise BadRequest(
                    "rating_product is required and must be an integer value."
                )

            main_product = request.env["product.custom.price"].sudo()
            model_reference = (
                request.env["ir.model"]
                .sudo()
                .search([("model", "=", main_product._name)])
            )
            product = main_product.browse(rating_product)

            if not product.exists():
                raise NotFound("Product does not exist.")

            user = self.get_user_by_id(user_id)
            if not user:
                raise NotFound("User not found!!")

            order = (
                request.env["ecommerce.orders"]
                .sudo()
                .search(
                    [
                        ("user.id", "=", user_id),
                        ("order_line_ids.product_id.id", "=", rating_product),
                        # ("status", "=", "delivered"),
                    ]
                )
            )

            if not order:
                raise BadRequest("The provided user is not eligible for the rating.")

            mail_message_master = request.env["mail.message"].sudo()
            check_rec = mail_message_master.search(
                [("model", "=", main_product._name), ("res_id", "=", rating_product),('parent_id',"=",None)]
            )
            if not check_rec:
                create_rec = mail_message_master.create(
                    {
                        "res_id": rating_product,
                        "author_id": user.commercial_partner_id.id,
                        "model": main_product._name,
                        "record_name": product.display_name,
                        "message_type": "comment",
                        "body": rating_comment,
                        "subtype_id": 1,
                        "email_from": f"{user.name},<{user.login}>",
                    }
                )
            else:
                create_rec = mail_message_master.create(
                    {
                        "parent_id": check_rec.id,
                        "res_id": rating_product,
                        "author_id": user.commercial_partner_id.id,
                        "model": main_product._name,
                        "record_name": product.display_name,
                        "message_type": "comment",
                        "body": rating_comment,
                        "subtype_id": 1,
                        "email_from": f"{user.name},<{user.login}>",
                    }
                )

            review_data = {
                "res_model_id": model_reference.id,
                "res_id": rating_product,
                "rating": rating_float,
                "feedback": rating_comment,
                "partner_id": user.commercial_partner_id.id,
                "consumed": True,
                "message_id": create_rec.id,
            }
            review_response_data = (
                request.env["rating.rating"].sudo().create(review_data)
            )
            print("review_response_data", review_response_data)

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": review_data,
                        # "review_response_data":review_response_data
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Bad Request"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Not Found"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/product/check-review-eligibility
    @http.route(
        "/api/v1/product/check-review-eligibility",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def product_check_review_eligibility(self):
        try:
            jwt_auth = jwt.JWTAuth()
            auth_status, status_code = jwt_auth.authenticate_request(request)
            if not auth_status["success"]:
                return Response(
                    json.dumps(auth_status),
                    content_type="application/json",
                    status=status_code,
                )
            user_id = auth_status["user_id"]
            request_data = request.httprequest.data
            data = json.loads(request_data)
            product_id = data.get("product_id")
            if product_id is None or not isinstance(product_id, int):
                raise BadRequest(
                    "product_id is required and it must be a type of integer."
                )

            order = (
                request.env["ecommerce.orders"]
                .sudo()
                .search(
                    [
                        ("user", "=", user_id),
                        ("order_line_ids.product_id", "=", product_id),
                        ("status", "=", "delivered"),
                    ]
                )
            )
            review_status = self.get_single_review_for_a_product(product_id, user_id)
            data = {
                "is_eligible": bool(order),
                "review_status": review_status,
            }
            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": data,
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # POST: /api/v1/user-activity
    @http.route(
        "/api/v1/user-activity",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
    )
    def user_activity(self):
        try:
            raw_data = request.httprequest.data
            data = json.loads(raw_data)
            user_id = data.get("user_id", None)
            product_id = data.get("product_id")
            session_id = data.get("session_id", None)
            search_query = data.get("search_query")
            activity_type = data.get("activity_type", None)
            country_name = data.get("country_name")
            country_code = data.get("country_code")
            user_ip = data.get("user_ip")

            if not user_id and not session_id:
                raise BadRequest("user_id or session_id is required.")

            if user_id and not isinstance(user_id, int):
                raise BadRequest("user_id must be of type integer.")

            if product_id and not isinstance(product_id, int):
                raise BadRequest("product_id must be of type integer.")

            user = request.env["res.users"].sudo().browse(user_id)
            product = request.env["product.custom.price"].sudo().browse(product_id)

            if user_id and not user.exists():
                raise NotFound("User doesn't exist.")

            if product_id and not product.exists():
                raise NotFound("Product doesn't exist.")

            if (
                not activity_type
                or not isinstance(activity_type, str)
                or activity_type not in ["view", "cart", "purchase", "search"]
            ):
                raise BadRequest(
                    "activity_type(string) is required and it can have value [view, cart,purchase,search] ."
                )
            if activity_type == "search" and search_query is None:
                raise BadRequest("search_query is required for activity_type search.")

            if activity_type == "cart" and product_id is None:
                raise BadRequest("product_id is required for activity_type cart.")

            if activity_type == "purchase" and product_id is None:
                raise BadRequest("product_id is required for activity_type purchase.")
            raw = {
                "user_id": user_id,
                "session_id": session_id if not user_id else None,
                "product_id": product_id,
                "activity_type": activity_type,
                "search_query": search_query,
                "country_name": country_name,
                "country_code": country_code,
                "request_ip": user_ip,
            }
            request.env["user.activity.log"].sudo().create(raw)
            return Response(
                json.dumps({"success": True, "data": raw}),
                content_type="application/json",
                status=200,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Not Found"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Bad Request"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": _("Something went wrong"),
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/product-recommendations
    @http.route(
        "/api/v1/product-recommendations",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def recommendations_based_on_user_activity(self):
        try:

            request_data = request.httprequest.data
            data = json.loads(request_data)
            user_id = data.get("user_id")
            session_id = data.get("session_id")

            if user_id is None and session_id is None:
                raise BadRequest("product_id or session_id is required.")
            if user_id and not isinstance(user_id, int):
                raise BadRequest("user_id must be of type integer.")

            if user_id and not self.get_user_by_id(user_id):
                raise NotFound("User not found!")

            recommendations = (
                request.env["product.custom.price"]
                .sudo()
                .get_advanced_recommendations(user_id=user_id, session_id=session_id)
            )
            recommended_products = []
            for rp in recommendations:
                product = rp.product_id
                recommended_products.append(
                    {
                        "product_id": product.id,
                        "product_name": product.name,
                        "discount": rp.discount,
                        "price_before_discount": self.price_before_discount(
                            rp.price_sell, rp.discount
                        ),
                        "price_sell": rp.price_sell or product.list_price,
                        "rating": {
                            "rating_count": rp.rating_count,
                            "rating_avg": rp.rating_avg,
                        },
                        "thumbnail_image_uri": self.get_thumbnail_uri(rp.id),
                        "product_url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{product.id}/{rp.company_id.id}",
                        "sold_by": {
                            "id": rp.company_id.id,
                            "name": rp.company_id.name,
                        },
                    }
                )

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {"recommended_products": recommended_products},
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    # GET: /api/v1/trending-products
    @http.route(
        "/api/v1/trending-products",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def trending_products(self):
        try:

            trending = (
                request.env["product.custom.price"].sudo().get_trending_products()
            )
            picks = []
            for rp in trending:
                product = rp.product_id
                picks.append(
                    {
                        "product_id": product.id,
                        "product_name": product.name,
                        "discount": rp.discount,
                        "price_before_discount": self.price_before_discount(
                            rp.price_sell, rp.discount
                        ),
                        "price_sell": rp.price_sell or product.list_price,
                        "rating": {
                            "rating_count": rp.rating_count,
                            "rating_avg": rp.rating_avg,
                        },
                        "thumbnail_image_uri": self.get_thumbnail_uri(rp.id),
                        "product_url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{product.id}/{rp.company_id.id}",
                        "sold_by": {
                            "id": rp.company_id.id,
                            "name": rp.company_id.name,
                        },
                    }
                )

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "data": {"trending_products": picks},
                    }
                ),
                content_type="application/json",
                status=200,
            )
        except BadRequest as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=400,
            )
        except NotFound as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ),
                content_type="application/json",
                status=404,
            )
        except Exception as e:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "message": "Something went wrong.",
                        "error": str(e),
                    }
                ),
                content_type="application/json",
                status=500,
            )

    def get_product_attributes(self, product):
        attributes = []
        for p in product.product_attributes_ids:
            if p.attribute_id.name == "Brand":
                for atr in p.value_ids:
                    attributes.append(
                        {
                            "id": p.attribute_id.id,
                            "name": _("Brand"),
                            "value": [
                                {
                                    "id": atr.id,
                                    "name": atr.name,
                                    "extra_price": self.get_extra_price(
                                        product, p.attribute_id.id, atr.id
                                    ),
                                }
                            ],
                        }
                    )
            else:

                vals = []
                for atr in p.value_ids:
                    vals.append(
                        {
                            "id": atr.id,
                            "name": atr.name,
                            "extra_price": self.get_extra_price(
                                product, p.attribute_id.id, atr.id
                            ),
                        }
                    )

                attributes.append(
                    {
                        "id": p.attribute_id.id,
                        "name": _(f"{p.attribute_id.name}"),
                        "value": vals,
                    }
                )

        return attributes

    def get_extra_price(self, product=None, attribute_id=None, value_id=None):

        if attribute_id is None or value_id is None or product is None:
            return 0

        product_attributes = product.product_attributes_ids.product_template_value_ids
        base_price = product.price_sell
        _product_attributes = product_attributes.search(
            [
                ("product_tmpl_id", "=", product.id),
                (
                    "product_attribute_value_id.attribute_id.id",
                    "=",
                    attribute_id,
                ),
                ("product_attribute_value_id.id", "=", value_id),
            ]
        )
        return _product_attributes.price_extra

    def get_recommended_products(self, product):
        main_product = product.product_recommendations
        products_list = []
        for p in main_product:
            products_list.append(
                {
                    "name": p.product_id.name,
                    "discount": p.discount,
                    "price_before_discount": self.price_before_discount(
                        p.price_sell, p.discount
                    ),
                    "price_sell": p.price_sell or 999,
                    "thumbnail_image_uri": self.get_thumbnail_uri(p.id),
                    "rating": {
                        "rating_count": p.rating_count,
                        "rating_avg": p.rating_avg,
                    },
                    "product_url": f"{ECOMMERCE_MAIN_DOMAIN}api/v1/products/{p.product_id.id}/{product.company_id.id}",
                    "sold_by": {
                        "id": p.company_id.id,
                        "name": p.company_id.name,
                    },
                }
            )
        return products_list

    def get_product_reviews(self, product_id=None):
        if product_id is None:
            return False
        product = (
            request.env["product.custom.price"]
            .sudo()
            .search([("id", "=", product_id)], limit=1)
        )
        if not product:
            return False
        product_reviews = []
        for review in product.rating_ids:
            product_reviews.append(
                {
                    "id": review.id,
                    "user": review.partner_id.name,
                    "rating": review.rating,
                    "rating_image_url": f"{ECOMMERCE_MAIN_DOMAIN}{review.rating_image_url}",
                    "feedback": review.feedback,
                    "feedback_image_url": [
                        f"{ECOMMERCE_MAIN_DOMAIN}{attachment.image_src}"
                        for attachment in review.message_id.attachment_ids
                    ]
                    or _("No Content"),
                    "published_date": str(review.create_date),
                }
            )

        return product_reviews

    def get_single_review_for_a_product(self, product_id, user_id):
        product = (
            request.env["product.custom.price"]
            .sudo()
            .search([("id", "=", product_id)], limit=1)
        )
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        rating = product.rating_ids.search(
            [
                ("res_id", "=", product_id),
                ("partner_id", "=", user.commercial_partner_id.id),
            ]
        )
        if rating:
            return "rated"
        else:
            return "not_rated"

    def price_before_discount(self, sell_price, discount):
        price_before_discount = (sell_price * discount / 100) + sell_price
        return price_before_discount

    def get_thumbnail_uri(self, product_id):
        uri = f"{ECOMMERCE_MAIN_DOMAIN}web/image?model=product.custom.price&id={product_id}&field=product_featured_image"
        return uri

    def get_featured_images(self, vendor_product_id=None, size=512):
        if vendor_product_id is None:
            return False
        record = request.env["product.custom.price"].search(
            [("id", "=", vendor_product_id)]
        )
        if not record:
            return f"{ECOMMERCE_MAIN_DOMAIN}/web/static/src/img/placeholder.png"
        variant_images = list(record.product_template_image_ids)
        featured_images = []
        for v in variant_images:
            featured_images.append(
                {
                    "name": v.name,
                    "uri": f"{ECOMMERCE_MAIN_DOMAIN}/web/image/{v._name}/{v.id}/image_{size}",
                }
            )

        return featured_images

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

    def get_sort_category_name(self, sort_by):
        sort_by_mapping = {
            "asc": _("Name in ascending order"),
            "dsc": _("Name in descending order"),
        }

        if sort_by in sort_by_mapping:
            return sort_by_mapping[sort_by]
        else:
            return "Default"

    def get_category_product_count(self, category_id):
        count = (
            request.env["product.template"]
            .sudo()
            .search_count([("categ_id", "=", category_id)])
        )
        if count < 1:
            return 0
        return count

    def get_product(self, product_id):
        return request.env["product.template"].sudo().search([("id", "=", product_id)])

    def get_vendor(self, vendor_id):
        return request.env["res.company"].sudo().search([("id", "=", vendor_id)])

    def get_main_product(self, product_id, vendor_id):
        return (
            request.env["product.custom.price"]
            .sudo()
            .search(
                [("product_id.id", "=", product_id), ("company_id.id", "=", vendor_id)],
                limit=1,
            )
        )

    def get_cart_product_attributes(self, cart_id):
        attributes = []
        cart = request.env["ecommerce.add.to.cart"].sudo().browse(cart_id)

        for p in cart.cart_attribute_ids:
            if p.attribute_id.name == "Brand":
                for atr in p.value_id:
                    attributes.append(
                        {
                            "id": p.attribute_id.id,
                            "name": _("Brand"),
                            "value": [{"id": atr.id, "name": atr.name}],
                        }
                    )
            else:

                vals = []
                for atr in p.value_id:
                    vals.append(
                        {
                            "id": atr.id,
                            "name": atr.name,
                        }
                    )

                attributes.append(
                    {
                        "id": p.attribute_id.id,
                        "name": _(f"{p.attribute_id.name}"),
                        "value": vals,
                    }
                )

        return attributes

    def get_wishlist_product_attributes(self, wishlist_id):
        attributes = []
        wishlist = request.env["ecommerce.wishlist"].sudo().browse(wishlist_id)

        for p in wishlist.wishlist_attribute_ids:
            if p.attribute_id.name == "Brand":
                for atr in p.value_id:
                    attributes.append(
                        {
                            "id": p.attribute_id.id,
                            "name": _("Brand"),
                            "value": [{"id": atr.id, "name": atr.name}],
                        }
                    )
            else:

                vals = []
                for atr in p.value_id:
                    vals.append(
                        {
                            "id": atr.id,
                            "name": atr.name,
                        }
                    )

                attributes.append(
                    {
                        "id": p.attribute_id.id,
                        "name": _(f"{p.attribute_id.name}"),
                        "value": vals,
                    }
                )

        return attributes

    def get_individual_cart_quantity(self, cart_id, user_id):
        total_quantity = (
            request.env["ecommerce.add.to.cart"]
            .sudo()
            .search(
                [
                    ("id", "=", cart_id),
                    ("user_id", "=", user_id),
                    ("status", "=", "active"),
                    ("quantity", ">", 0),
                ]
            )
            .mapped("quantity")
        )

        return sum(total_quantity)

    def get_user_by_id(self, id):
        user = request.env["res.users"].sudo().search([("id", "=", id)], limit=1)
        if not user:
            return False
        return user
