from odoo import http, _
from odoo.http import request
import json
import uuid
import requests

class AddToCartWishlist(http.Controller):

    @http.route(
        ["/add-to-cart"],
        type="json",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def add_to_cart(self, **kwargs):
        try:
            product_id = int(kwargs.get("product_id", 0))
            qty = int(kwargs.get("qty", 1))
            attributes = kwargs.get("attr", [])
            user_id = int(kwargs.get("user_id", 0))
            unit_price = float(kwargs.get("unit_price", 0.0))

            user = request.env["res.users"].sudo().browse(user_id)
            if not user:
                return {"success": False, "message": "Invalid user"}

            product = request.env["product.custom.price"].sudo().browse(product_id)
            if not product:
                return {"success": False, "message": "Invalid product"}

            attribute_value_pairs = [
                (int(attr.split("-")[0]), int(attr.split("-")[1]))
                for attr in attributes
            ]

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

                if sorted(cart_item_attributes) == sorted(attribute_value_pairs):
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

                for attr in attribute_value_pairs:
                    try:
                        attribute_id, value_id = attr
                        attribute = (
                            request.env["cp.attribute"].sudo().browse(attribute_id)
                        )
                        value = (
                            request.env["cp.attribute.value"].sudo().browse(value_id)
                        )

                        if not attribute or not value:
                            return {
                                "success": False,
                                "message": f"Invalid attribute or value for {attribute_id}-{value_id}",
                            }

                        request.env["ecommerce.cart.attributes"].sudo().create(
                            {
                                "cart_id": cart.id,
                                "attribute_id": attribute_id,
                                "value_id": value_id,
                            }
                        )
                    except ValueError:
                        return {
                            "success": False,
                            "message": f"Invalid attribute format for {attr}",
                        }

            cart_quantity = request.env["website"].sudo().get_cart_quantity()
            individual_quantity = (
                request.env["ecommerce.add.to.cart"]
                .sudo()
                .get_individual_cart_quantity(product_id)
            )

            return {
                "success": True,
                "message": "Product added to cart",
                "cart_id": cart_id,
                "name": product.product_id.name,
                "individual_qty": individual_quantity,
                "price_total": int(individual_quantity) * unit_price or 1,
                "cart_quantity": cart_quantity,
                "image_url": product.website_id.image_url(
                    product, "product_featured_image"
                ),
            }

        except Exception as e:
            return {"success": False, "message": str(e)}

    @http.route(
        ["/add-to-wishlist"],
        type="json",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def add_to_wishlist(self, **kwargs):
        try:
            product_id = int(kwargs.get("product_id", 0))
            attributes = kwargs.get("attr", [])
            user_id = int(kwargs.get("user_id", 0))
            user = request.env["res.users"].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "message": "Invalid user"}

            product = request.env["product.custom.price"].sudo().browse(product_id)
            if not product.exists():
                return {"success": False, "message": "Invalid product"}
            check_wishlist = (
                request.env["ecommerce.wishlist"]
                .sudo()
                .check_if_wishlist_exists(product_id)
            )
            if check_wishlist:
                return {
                    "success": False,
                    "message": f"{product.product_id.name} {_('is already in your wishlist')}",
                }
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

            for attr in attributes:
                try:
                    attribute_id, value_id = map(int, attr.split("-"))
                    attribute = request.env["cp.attribute"].sudo().browse(attribute_id)
                    value = request.env["cp.attribute.value"].sudo().browse(value_id)

                    if not attribute or not value:
                        return {
                            "success": False,
                            "message": f"Invalid attribute or value for {attr}",
                        }

                    request.env["ecommerce.wishlist.attributes"].sudo().create(
                        {
                            "wishlist_id": wishlist.id,
                            "attribute_id": attribute_id,
                            "value_id": value_id,
                        }
                    )
                except ValueError:
                    return {
                        "success": False,
                        "message": f"Invalid attribute format for {attr}",
                    }
            wishlist_count = request.env["ecommerce.wishlist"].get_wishlist()

            check_wishlist = request.env["ecommerce.wishlist"].check_if_wishlist_exists(
                product.id
            )
            individual_wishlist_count = request.env[
                "ecommerce.wishlist"
            ].wishlist_count(product.id)
            template = (
                request.env["ir.ui.view"]
                .sudo()
                ._render_template(
                    "base_accounting_kit.wishlist_count",
                    {
                        "wishlist": check_wishlist,
                        "wishlist_count": individual_wishlist_count,
                    },
                )
            )

            return {
                "success": True,
                "item": wishlist.product_id.product_id.name,
                "wishlist_id": wishlist.id,
                "wishlist_count": wishlist_count,
                "wishlist_template": template,
            }

        except Exception as e:
            return {"success": False, "message": str(e)}
        
        
    @http.route(
        ["/add-to-wishlist-products"],
        type="json",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def add_to_wishlist_products_page(self, **kwargs):
        try:
            product_id = int(kwargs.get("product_id", 0))
            user_id = int(kwargs.get("user_id", 0))
            user = request.env["res.users"].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "message": "Invalid user"}

            product = request.env["product.custom.price"].sudo().browse(product_id)

            attr = product.product_attributes_ids[:1]
            attributes=[]
            if attr and attr.attribute_id and attr.value_ids:
                attributes.append(f"{attr.attribute_id.id}-{attr.value_ids[0].id}")
                            
            if not product.exists():
                return {"success": False, "message": "Invalid product"}
            check_wishlist = (
                request.env["ecommerce.wishlist"]
                .sudo()
                .check_if_wishlist_exists(product_id)
            )
            if check_wishlist:
                return {
                    "success": False,
                    "message": f"{product.product_id.name} {_('is already in your wishlist')}",
                }
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

            for attr in attributes:
                try:
                    attribute_id, value_id = map(int, attr.split("-"))
                    attribute = request.env["cp.attribute"].sudo().browse(attribute_id)
                    value = request.env["cp.attribute.value"].sudo().browse(value_id)

                    if not attribute or not value:
                        return {
                            "success": False,
                            "message": f"Invalid attribute or value for {attr}",
                        }

                    request.env["ecommerce.wishlist.attributes"].sudo().create(
                        {
                            "wishlist_id": wishlist.id,
                            "attribute_id": attribute_id,
                            "value_id": value_id,
                        }
                    )
                except ValueError:
                    return {
                        "success": False,
                        "message": f"Invalid attribute format for {attr}",
                    }
            wishlist_count = request.env["ecommerce.wishlist"].get_wishlist()

            check_wishlist = request.env["ecommerce.wishlist"].check_if_wishlist_exists(
                product.id
            )

            return {
                "success": True,
                "message": f"{wishlist.product_id.product_id.name} {_('is added to you wishlist')}",
                "wishlist_id": wishlist.id,
                "wishlist_count": wishlist_count,
            }

        except Exception as e:
            return {"success": False, "message": str(e)}

    @http.route(
        ["/my/cart"],
        methods=["GET"],
        type="http",
        auth="user",
        website=True,
    )
    def my_cart(self, **kwargs):

        my_cart = (
            request.env["ecommerce.add.to.cart"]
            .sudo()
            .get_my_cart(user_id=request.env.user.id)
        )
        related_companies = (
            request.env["ecommerce.add.to.cart"]
            .sudo()
            .get_related_companies(user_id=request.env.user.id)
        )
        return request.render(
            "base_accounting_kit.my_cart",
            {"my_cart": my_cart, "related_companies": related_companies},
        )

    @http.route(
        ["/update-cart"],
        methods=["POST"],
        type="json",
        auth="user",
        csrf=False,
        website=True,
    )
    def update_cart(self, **kwargs):
        cart_id = int(kwargs.get("cart_id", 0))
        qty = kwargs.get("qty", 0)
        user_id = int(kwargs.get("user_id", 0))
        try:
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

            my_cart.sudo().write(
                {
                    "quantity": qty,
                }
            )
            cart_quantity = request.env["website"].sudo().get_cart_quantity()

            return {
                "success": True,
                "cart_quantity": cart_quantity,
                "message": "Cart Updated Successfully!",
            }
        except Exception as e:
            return {"success": False, "message": e}

    @http.route(
        ["/proceed-to-checkout"],
        methods=["POST"],
        type="http",
        auth="user",
        website=True,
    )
    def proceed_to_checkout(self, **kwargs):

        my_orders_str = kwargs.get("my_orders[]", "[]")
        t_amt = kwargs.get("t_amt", 0)
        try:
            if float(t_amt) < 1:
                return request.redirect(f"/bad-request?spam={str(uuid.uuid4())}")

            total_items = 0
            total_items_price = 0

            if kwargs.get("type") == "cart":
                my_orders = json.loads(my_orders_str)
                cart_ids = [order.get("cart_id") for order in my_orders]
                items = (
                    request.env["ecommerce.add.to.cart"]
                    .sudo()
                    .get_carts_by_ids(cart_ids)
                )
                total_price_without_voucher = 0
                for cart in items:
                    total_price_without_voucher += (
                        cart.product_id.price_sell * cart.quantity
                    )
                # if float(total_price_without_voucher) != float(t_amt):
                #     return request.redirect(request.httprequest.referrer or "/")

                for i in items:
                    total_items += i.quantity
                    total_items_price += i.quantity * i.price_unit

                related_companies = (
                    request.env["ecommerce.add.to.cart"]
                    .sudo()
                    .get_related_companies_by_cart_ids(
                        user_id=request.env.user.id, items=items
                    )
                )

            shipping_addresses = (
                request.env["res.partner"]
                .sudo()
                .get_addresses(request.env.user.commercial_partner_id.id, "delivery")
            )
            billing_address = (
                request.env["res.partner"]
                .sudo()
                .get_addresses(request.env.user.commercial_partner_id.id, "invoice")
            )
            company_main_config = request.env["ecommerce.main.settings"].sudo()
            company_delivery_config = request.env["ecommerce.delivery.charges"].sudo()
            user_default_delivery_location = request.env[
                "res.partner"
            ].get_default_address("shipping", request.env.user.commercial_partner_id.id)
            return request.render(
                "base_accounting_kit.checkout",
                {
                    "items": items,
                    "my_orders_str": my_orders_str,
                    "related_companies": related_companies,
                    "shipping_addresses": shipping_addresses,
                    "billing_address": billing_address,
                    "total_items": total_items,
                    "total_items_price": total_items_price,
                    "company_main_config": company_main_config,
                    "company_delivery_config": company_delivery_config,
                    "partner_latitude": user_default_delivery_location.partner_latitude,
                    "partner_longitude": user_default_delivery_location.partner_longitude,
                },
            )
        except Exception as e:
            print("Error decoding the my_orders[] string.", e)

    @http.route(
        ["/my/wishlist"],
        methods=["GET"],
        type="http",
        auth="user",
        website=True,
    )
    def my_wishlist(self, **kwargs):
        my_wishlist = (
            request.env["ecommerce.wishlist"]
            .sudo()
            .get_wishlist_record(user_id=request.env.user.id)
        )
        related_companies = (
            request.env["ecommerce.wishlist"]
            .sudo()
            .get_related_companies(user_id=request.env.user.id)
        )
        return request.render(
            "base_accounting_kit.my_wishlist",
            {"my_wishlist": my_wishlist, "related_companies": related_companies},
        )

    @http.route(
        ["/remove_from_wishlist"],
        type="json",
        auth="user",
        website=True,
    )
    def remove_my_wishlist(self, **kwargs):
        wishlist_ids = kwargs.get("params", {}).get("wishlist_ids", [])
        # if not isinstance(product_ids, list):
        #     return {'error': 'Invalid product_ids'}
        Wishlist = request.env["ecommerce.wishlist"]
        for wishlist_id in wishlist_ids:
            wishlist_items = Wishlist.search([("id", "=", wishlist_id)])
            wishlist_items.unlink()
        return {"status": "success", "message": "Products removed from wishlist"}

    @http.route(["/unlink_data"], type="json", auth="user", csrf=False)
    def unlink_data(self, **kwargs):
        try:
            type = kwargs.get("type", None)
            id = kwargs.get("id", None)
            if not type or not id:
                return {
                    "success": False,
                    "message": _("Both type and id are required."),
                }
            # if type=='cart':

            model = request.env["ecommerce.add.to.cart"].sudo()
            domain = [("user_id", "=", request.env.user.id), ("id", "=", id)]
            if type == "wishlist":
                model = request.env["ecommerce.wishlist"].sudo()
            count = model
            model = model.search(domain)
            if not model:
                return {"success": False, "message": _("Bad request!")}

            model.unlink()
            data_count = count.search_count([("user_id", "=", request.env.user.id)])

            template = None
            if type == "wishlist":
                my_wishlist = (
                    request.env["ecommerce.wishlist"]
                    .sudo()
                    .get_wishlist_record(user_id=request.env.user.id)
                )
                related_companies = (
                    request.env["ecommerce.wishlist"]
                    .sudo()
                    .get_related_companies(user_id=request.env.user.id)
                )
                template = (
                    request.env["ir.ui.view"]
                    .sudo()
                    ._render_template(
                        "base_accounting_kit.my_wishlist1",
                        {
                            "my_wishlist": my_wishlist,
                            "related_companies": related_companies,
                        },
                    )
                )
                return {"success": True, "data": template, "data_count": data_count}

            else:
                my_cart = (
                    request.env["ecommerce.add.to.cart"]
                    .sudo()
                    .get_my_cart(user_id=request.env.user.id)
                )
                related_companies = (
                    request.env["ecommerce.add.to.cart"]
                    .sudo()
                    .get_related_companies(user_id=request.env.user.id)
                )
                template = (
                    request.env["ir.ui.view"]
                    .sudo()
                    ._render_template(
                        "base_accounting_kit.my_cart_main",
                        {"my_cart": my_cart, "related_companies": related_companies},
                    )
                )
                cart_quantity = request.env["website"].sudo().get_cart_quantity()

                return {
                    "success": True,
                    "data": template,
                    "cart_quantity": cart_quantity,
                    "message": "Cart Updated Successfully!",
                }
        except Exception as e:
            return {
                "success": False,
                "message": e,
            }

    @http.route(
        ["/remove_from_cart"],
        type="json",
        auth="user",
        website=True,
    )
    def remove_from_cart(self, **kwargs):
        try:
            cart_ids = kwargs.get("params", {}).get("cart_ids", [])
            cartList = request.env["ecommerce.add.to.cart"]
            for cart_id in cart_ids:
                cartlist_items = cartList.search([("id", "=", cart_id)])
                cartlist_items.unlink()
            my_cart = (
                request.env["ecommerce.add.to.cart"]
                .sudo()
                .get_my_cart(user_id=request.env.user.id)
            )
            related_companies = (
                request.env["ecommerce.add.to.cart"]
                .sudo()
                .get_related_companies(user_id=request.env.user.id)
            )
            template = (
                request.env["ir.ui.view"]
                .sudo()
                ._render_template(
                    "base_accounting_kit.my_cart_main",
                    {"my_cart": my_cart, "related_companies": related_companies},
                )
            )
            cart_quantity = request.env["website"].sudo().get_cart_quantity()
            return {
                "success": True,
                "cart_quantity": cart_quantity,
                "refresh_template": template,
            }
        except Exception as e:
            return {"success": False, "message": e}

    @http.route(
        ["/cart_to_wishlist"],
        type="json",
        auth="user",
        website=True,
    )
    def add_to_wishlist_fromcart(self, **kwargs):
        cart_id = kwargs.get("cart_id")
        cart = (
            request.env["ecommerce.add.to.cart"].sudo().search([("id", "=", cart_id)])
        )
        attributes_ids = []
        attr_key_value_pair = []
        for attr in cart.cart_attribute_ids:
            attr_key_value_pair.append((attr.attribute_id.id, attr.value_id.id))
            attributes_ids.append(
                (
                    0,
                    0,
                    {
                        "attribute_id": attr.attribute_id.id,
                        "value_id": attr.value_id.id,
                    },
                )
            )

        wishlist_model = request.env["ecommerce.wishlist"].sudo()

        wishlist_ = wishlist_model.search(
            [
                ("user_id", "=", request.env.user.id),
                ("product_id", "=", cart.product_id.id),
            ]
        )

        wishlist_with_attributes = None
        for wishlist_item_item in wishlist_:
            cart_item_attributes = [
                (attr.attribute_id.id, attr.value_id.id)
                for attr in wishlist_item_item.wishlist_attribute_ids
            ]

            if sorted(cart_item_attributes) == sorted(attr_key_value_pair):
                wishlist_with_attributes = wishlist_item_item
                break

        if wishlist_with_attributes:
            return {
                "success": False,
                "message": f'{cart.product_id.product_id.name} { _("is already in your wishlist.")}',
            }
        wishlist = wishlist_model.create(
            {
                "user_id": request.env.user.id,
                "product_id": cart.product_id.id,
                "wishlist_attribute_ids": attributes_ids,
            }
        )
        wishlist_count = wishlist_model.search_count(
            [
                ("user_id", "=", request.env.user.id),
            ]
        )
        if wishlist:
            return {
                "success": True,
                "data": f'{cart.product_id.product_id.name} { _("is added to your wishlist.")}',
                "len": wishlist_count,
            }
        else:
            return {
                "success": False,
                "message": "Error while adding products to wishlist.",
            }

    @http.route(
        ["/wishlist_to_cart"],
        type="json",
        auth="user",
        website=True,
    )
    def add_to_cart_fromwishlist(self, **kwargs):
        wishlist_id = kwargs.get("params", {}).get("wishlist_id", [])
        wishlist = request.env["ecommerce.wishlist"].search([("id", "=", wishlist_id)])
        product = (
            request.env["product.custom.price"].sudo().browse(wishlist.product_id.id)
        )
        if not product:
            return {"success": False, "message": "Invalid product"}
        cart = (
            request.env["ecommerce.add.to.cart"]
            .sudo()
            .search(
                [
                    ("user_id", "=", request.env.user.id),
                    ("product_id", "=", product.id),
                    ("status", "in", ["active"]),
                ],
                limit=1,
                order="added_date asc",
            )
        )

        if cart:
            cart.write(
                {
                    "quantity": cart.quantity + 1,
                }
            )
            cart_quantity = request.env["website"].sudo().get_cart_quantity()
            return_vals = {
                "success": True,
                "cart_quantity": cart_quantity,
                "message": _("Products added to cart successfully."),
            }
        else:
            # attributes=
            new_cart = (
                request.env["ecommerce.add.to.cart"]
                .sudo()
                .create(
                    {
                        "user_id": request.env.user.id,
                        "product_id": product.id,
                        "quantity": product.min_qty,
                        "price_unit": product.price_sell
                        - (product.price_sell * product.discount / 100),
                    }
                )
            )
            cart_id = new_cart.id
            if new_cart:
                for attrs in wishlist.wishlist_attribute_ids:
                    request.env["ecommerce.cart.attributes"].sudo().create(
                        {
                            "cart_id": cart_id,
                            "attribute_id": attrs.attribute_id.id,
                            "value_id": attrs.value_id.id,
                        }
                    )
                cart_quantity = request.env["website"].sudo().get_cart_quantity()

                return_vals = {
                    "success": True,
                    "cart_quantity": cart_quantity,
                    "message": _("Products added to cart successfully."),
                }

            else:
                return {
                    "success": False,
                    "message": _("Error while adding products to cart."),
                }

        wishlist.unlink()
        my_wishlist = (
            request.env["ecommerce.wishlist"]
            .sudo()
            .get_wishlist_record(user_id=request.env.user.id)
        )
        related_companies = (
            request.env["ecommerce.wishlist"]
            .sudo()
            .get_related_companies(user_id=request.env.user.id)
        )
        template = (
            request.env["ir.ui.view"]
            .sudo()
            ._render_template(
                "base_accounting_kit.my_wishlist1",
                {
                    "my_wishlist": my_wishlist,
                    "related_companies": related_companies,
                },
            )
        )
        return_vals["refresh_template"] = template

        return return_vals
