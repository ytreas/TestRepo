from odoo import http, _
from odoo.http import request


class EcommerceUserController(http.Controller):

    @http.route("/api/v1/user/signup", methods=["POST"], cors="*", csrf=False)
    def signup(self):
        pass
