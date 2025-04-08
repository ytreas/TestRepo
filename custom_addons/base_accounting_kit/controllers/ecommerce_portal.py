from odoo import http
from odoo.http import Response, request
from odoo.addons.website_sale.controllers import main
from odoo.addons.website.controllers.main import QueryURL


class CustomProduct(http.Controller):

    @http.route(
        [
            '/shop/<model("product.template"):product>/<model("product.custom.price"):stock>'
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def get_custom_product_details(self, product, stock, **kwargs):
        
        try:
            
            print("==============Stock ==================")
            print(stock)
            # print(stock.company_id)
            print("==============Stock ==================")
            return request.render(
                "website_sale.product",
                self._prepare_product_values(
                    product=product,stock=stock, category="", search="", **kwargs
                ),
            )
        except Exception as e:
            print('error',e)

    def _product_get_query_url_kwargs(self, category, search, attrib=None, **kwargs):
        return {
            "category": category,
            "search": search,
            "attrib": attrib,
            "tags": kwargs.get("tags"),
            "min_price": kwargs.get("min_price"),
            "max_price": kwargs.get("max_price"),
        }

    def _prepare_product_values(self, product,stock, category, search, **kwargs):
        ProductCategory = request.env["product.public.category"]

        if category:
            category = ProductCategory.browse(int(category)).exists()

        attrib_list = request.httprequest.args.getlist("attrib")
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attrib_set = {v[1] for v in attrib_values}

        keep = QueryURL(
            "/shop",
            **self._product_get_query_url_kwargs(
                category=category and category.id,
                search=search,
                **kwargs,
            ),
        )

        # Needed to trigger the recently viewed product rpc
        view_track = request.website.viewref("website_sale.product").track

        return {
            "search": search,
            "category": category,
            "pricelist": request.website.pricelist_id,
            "attrib_values": attrib_values,
            "attrib_set": attrib_set,
            "keep": keep,
            "categories": ProductCategory.search([("parent_id", "=", False)]),
            "main_object": product,
            "product": product,
            "stock":stock,
            "add_qty": 1,
            "view_track": view_track,
        }

    @http.route(["/say-hello"], type="http", auth="public", website=True, sitemap=True)
    def say_hello(self):

        print("=========HELLO WORLD=========")
        print("=========HELLO WORLD=========")
        print("=========HELLO WORLD=========")
        print("=========HELLO WORLD=========")
    
    
    # @http.route(
    #     [
    #         '/vendor/<model("res.company"):vendor>'
    #     ],
    #     type="http",
    #     auth="public",
    #     website=True,
    #     sitemap=True,
    # )
    # def visit_vendor(self, vendor,**kwargs):
    #     branch_products = request.env['product.custom.price'].sudo().search([('company_id','=',vendor.id)])
    #     ribbon_id=request.env['product.ribbon'].sudo().search([('id','=',10)])
    #     # Prepare product data
    #     products_with_custom_pricing = []
    #     for branch_product in branch_products:
    #         product = branch_product.product_id
    #         products_with_custom_pricing.append({
    #             'product': product,   
    #             'custom_product': branch_product,   
    #             'price': branch_product.price_sell or product.list_price,
    #             'attributes': branch_product.saleable_qty or product.description,
    #             'branch': branch_product.company_id,
    #             'x':1,
    #             'y':1,
    #             'ribbon':ribbon_id,
    #         })
            
    #     values={
    #         'products_with_custom_pricing':products_with_custom_pricing
    #     }
    #     return request.render('base_accounting_kit.vendor_details',values)
        
