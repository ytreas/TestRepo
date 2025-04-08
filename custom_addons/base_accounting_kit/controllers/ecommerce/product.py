from odoo import http, _
from odoo.http import request


class CustomProduct(http.Controller):

    @http.route(
        ["/products/<model('product.template'):product>/<model('res.company'):vendor>"],
        methods=["GET"],
        type="http",
        website=True,
        auth="public",
    )
    def product_view(self, product, vendor, **kwargs):
        vendor_product = (
            request.env["product.custom.price"]
            .sudo()
            .search(
                [("company_id", "=", vendor.id), ("product_id", "=", product.id)],
                limit=1,
            )
        )

        wishlist = request.env["ecommerce.wishlist"].check_if_wishlist_exists(
            vendor_product.id
        )
        wishlist_count = request.env["ecommerce.wishlist"].wishlist_count(
            vendor_product.id
        )

        return request.render(
            "base_accounting_kit.ecommerce_product_view",
            {
                "product": product,
                "vendor": vendor,
                "vendor_product": vendor_product,
                "wishlist": wishlist,
                "wishlist_count": wishlist_count,
            },
        )

    @http.route(["/wishlist_counter"], type="json", csrf=False, auth="user")
    def wishlist_counter(self, **data):
        vendor_id = data.get("vendor_id", False)
        product_id = data.get("vendor_id", False)
        if not vendor_id and not product_id:
            return {
                "success": False,
                "message": _("Vendor and product id are required"),
            }
        vendor_product = (
            request.env["product.custom.price"]
            .sudo()
            .search(
                [("company_id", "=", vendor_id), ("product_id", "=", product_id)],
                limit=1,
            )
        )
        wishlist = request.env["ecommerce.wishlist"].check_if_wishlist_exists(
            vendor_product.id
        )
        wishlist_count = request.env["ecommerce.wishlist"].wishlist_count(
            vendor_product.id
        )
        template = (
            request.env["ir.ui.view"]
            .sudo()
            ._render_template(
                "base_accounting_kit.wishlist_count",
                {"wishlist": wishlist, "wishlist_count": wishlist_count},
            )
        )

        return {"success": True, "data": template}
