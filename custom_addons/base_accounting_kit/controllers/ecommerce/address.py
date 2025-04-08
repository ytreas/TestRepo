from odoo import http, _
from odoo.http import request
import json


class AddressConfiguration(http.Controller):

    @http.route(["/save_address"], type="json", auth="user", csrf=False, website=True)
    def save_address(self, **kwargs):
        fullname = kwargs.get("fullname", "")
        phone = kwargs.get("phone", "")
        email = kwargs.get("email", "")
        street = kwargs.get("street", "")
        address = kwargs.get("address", "")
        type = kwargs.get("type", "shipping")
        latitude = kwargs.get("latitude", None)
        longitude = kwargs.get("longitude", None)

        actual_type = "delivery"
        if type == "invoicing":
            actual_type = "invoice"
        # try:
        #     address = (
        #         request.env["ecommerce.user.address"]
        #         .sudo()
        #         .create(
        #             {
        #                 "user": request.env.user.id,
        #                 "fullname": fullname,
        #                 "phone_number": phone,
        #                 "email": email,
        #                 "address": address,
        #                 "street": street,
        #                 "type": type,
        #             }
        #         )
        #     )
        #     return {"success": True, "message": _("Address created successfully!")}
        # except Exception as e:
        #     return {"success": False, "message": e}
        try:
            address = (
                request.env["res.partner"]
                .sudo()
                .create(
                    {
                        "commercial_partner_id": request.env.user.commercial_partner_id.id,
                        "name": fullname,
                        "parent_id": request.env.user.commercial_partner_id.id,
                        "user_id": request.env.user.id,
                        "complete_name": f"{request.env.user.name}, {fullname}",
                        "type": actual_type,
                        "street": address,
                        "street2": street,
                        "email": email,
                        "mobile": phone,
                        "active": True,
                        "partner_latitude": latitude,
                        "partner_longitude": longitude,
                    }
                )
            )
            return {"success": True, "data": _("Address created successfully!")}
        except Exception as e:
            return {"success": False, "message": e}

    @http.route(
        "/render_address_modal_view", type="json", auth="user", website=True, csrf=False
    )
    def render_address_modal_view(self, **kwargs):
        return {
            "data": request.env["ir.ui.view"]._render_template(
                "base_accounting_kit.address_modal_body", {}
            )
        }

    @http.route(
        "/update_main_address_view", type="json", auth="user", website=True, csrf=False
    )
    def update_main_address_view(self, **kwargs):
        commercial_partner_id = request.env.user.commercial_partner_id.id
        shipping_addresses = (
            request.env["res.partner"]
            .sudo()
            .get_addresses(commercial_partner_id, "delivery")
        )
        billing_address = (
            request.env["res.partner"]
            .sudo()
            .get_addresses(commercial_partner_id, "invoice")
        )
        return {
            "data": request.env["ir.ui.view"]._render_template(
                "base_accounting_kit.js_main_address_modal",
                {
                    "shipping_addresses": shipping_addresses,
                    "billing_address": billing_address,
                },
            )
        }

    @http.route("/change_address", type="json", auth="user", website=True, csrf=False)
    def change_address(self, **kwargs):

        try:
            main = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [
                        ("id", "=", kwargs.get("address_id", 1)),
                        (
                            "commercial_partner_id",
                            "=",
                            request.env.user.commercial_partner_id.id,
                        ),
                    ]
                )
            )
            selected_address = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [
                        ("address_selected", "=", True),
                        (
                            "commercial_partner_id",
                            "=",
                            request.env.user.commercial_partner_id.id,
                        ),
                    ]
                )
            )
            selected_address.sudo().write({"address_selected": False})
            main.sudo().write(
                {
                    "address_selected": True,
                }
            )
            return {
                "success": True,
                "message": _("Default address updated successfully!"),
            }

        except Exception as e:
            return {"success": False, "message": e}

    @http.route("/delete_address", type="json", auth="user", website=True, csrf=False)
    def delete_address(self, **kwargs):

        try:
            main = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [
                        ("id", "=", kwargs.get("card_id", 1)),
                        (
                            "commercial_partner_id",
                            "=",
                            request.env.user.commercial_partner_id.id,
                        ),
                    ]
                )
            )
            if main:
                main.sudo().unlink()
                return {
                    "success": True,
                    "message": _("The address deleted successfully!"),
                }
            else:
                return {
                    "success": False,
                    "message": _("The given address does not exist."),
                }

        except Exception as e:
            return {"success": False, "message": e}

    @http.route(
        "/get_default_addresses", type="json", auth="user", website=True, csrf=False
    )
    def get_default_addresses(self, **kwargs):
        default_billing = (
            request.env["res.partner"]
            .sudo()
            .search(
                [
                    (
                        "commercial_partner_id",
                        "=",
                        request.env.user.commercial_partner_id.id,
                    ),
                    ("type", "=", "invoice"),
                ],
                limit=1,
            )
        )
        default_shipping = (
            request.env["res.partner"]
            .sudo()
            .search(
                [
                    (
                        "commercial_partner_id",
                        "=",
                        request.env.user.commercial_partner_id.id,
                    ),
                    ("type", "=", "delivery"),
                    ("address_selected", "=", True),
                ],
                limit=1,
            )
        )

        return {
            "default_address": request.env["ir.ui.view"]._render_template(
                "base_accounting_kit.default_address",
                {
                    "default_billing": default_billing,
                    "default_shipping": default_shipping,
                },
            )
        }

    @http.route(
        "/refresh_products_delivery_charges",
        type="json",
        auth="user",
        website=True,
        csrf=False,
    )
    def refresh_products_delivery_charges(self, **kwargs):
        try:
            my_orders_str = kwargs.get("order", "[]")
            my_orders = json.loads(my_orders_str)
            cart_ids = [order.get("cart_id") for order in my_orders]
            items = (
                request.env["ecommerce.add.to.cart"].sudo().get_carts_by_ids(cart_ids)
            )

            related_companies = (
                request.env["ecommerce.add.to.cart"]
                .sudo()
                .get_related_companies_by_cart_ids(
                    user_id=request.env.user.id, items=items
                )
            )
            company_main_config = request.env["ecommerce.main.settings"].sudo()
            company_delivery_config = request.env["ecommerce.delivery.charges"].sudo()
            user_default_delivery_location = request.env[
                "res.partner"
            ].get_default_address("shipping", request.env.user.commercial_partner_id.id)
            template = request.env["ir.ui.view"]._render_template(
                "base_accounting_kit.shipping_product_details",
                {
                    "items": items,
                    "related_companies": related_companies,
                    "company_main_config": company_main_config,
                    "company_delivery_config": company_delivery_config,
                    "partner_latitude": user_default_delivery_location.partner_latitude,
                    "partner_longitude": user_default_delivery_location.partner_longitude,
                },
            )
            return {"success": True, "template": template}
        except Exception as e:
            return {"success": False, "message": e}
