# from odoo.addons.web.controllers.home import Home
from odoo.http import Response, request
from odoo import http,api,SUPERUSER_ID
from odoo.addons.web.controllers.home import Home
import jwt
import datetime
import logging
import os
import datetime
from dotenv import load_dotenv


class LoginPageInherit(Home):
    @http.route()
    def web_login(self, redirect=None, **kw):
        try:
            # Get host URL
            hosturl = request.httprequest.environ['HTTP_REFERER'] if request else 'n/a'
            print("Host URL (before processing):", hosturl)
            hosturl = hosturl[hosturl.index('://')+3:]
            hosturl = hosturl[:hosturl.index('/')]
            print("Host URL (after processing):", hosturl)
            
            # Fetch company details based on URL
            company_detail = http.request.env["res.company.details"].sudo().search([('url', '=', hosturl)])
            print("Company Details:", company_detail)
            
            company = company_detail.parent_id
            print("Parent Company:", company)
            
            # Set company-specific background image and logo
            request.company_bg_img = company.login_bg_img if company.login_bg_img else False
            print("Company Background Image:", request.company_bg_img)
            
            request.company_logo = company.logo if company.logo else False
            print("Company Logo:", request.company_logo)

            # Handle language-specific titles and information
            if request.env.context['lang'] == 'ne_NP':
                request.company_palika_info = company.palika.palika_name_np if company.palika.palika_name_np else False
                request.company_title1 = str(company.palika.type_np) + ' कार्यपालिकाको कार्यालय' if company.palika.type_np else False
                request.company_title2 = company.street_np if company.street_np else False
                request.company_title3 = str(company.province.name_np) + ', नेपाल' if company.province.name_np else False

                print("Company Palika Info (Nepali):", request.company_palika_info)
                print("Company Title 1 (Nepali):", request.company_title1)
                print("Company Title 2 (Nepali):", request.company_title2)
                print("Company Title 3 (Nepali):", request.company_title3)
            else:
                request.company_palika_info = company.palika.palika_name if company.palika.palika_name else False
                request.company_title1 = "Office of " + str(company.palika.type) + ' Executive' if company.palika.type else False
                request.company_title2 = company.street if company.street else False
                request.company_title3 = str(company.province.name) + ', Nepal' if company.province.name else False

                print("Company Palika Info (English):", request.company_palika_info)
                print("Company Title 1 (English):", request.company_title1)
                print("Company Title 2 (English):", request.company_title2)
                print("Company Title 3 (English):", request.company_title3)

            # Call the original web_login method
            res = super().web_login(redirect, **kw)
        except Exception as e:
            print("Exception occurred:", str(e))
            res = super().web_login(redirect, **kw)
        return res