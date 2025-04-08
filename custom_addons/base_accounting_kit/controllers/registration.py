from odoo.http import Response, request
from odoo import http,api,SUPERUSER_ID
import datetime
from datetime import date
from . import jwt_token_auth
import logging
import json
import base64
import re


_logger = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "webp"}
class Registration(http.Controller):
    def validate_company_data(self, company_type, pan_number, mobile, email, name):
        """Validate company registration constraints"""
        # Validate PAN Number
        if pan_number and (not pan_number.isdigit() or len(pan_number) != 9):
            return {"message": "PAN Number must be exactly 9 digits long."}

        # Validate Mobile Number
        if mobile and (not mobile.isdigit() or len(mobile) != 10 or not mobile.startswith(("97", "98"))):
            return {"message": "Mobile number must be 10 digits long and start with 97 or 98."}

        # Validate Email Format
        if email:
            email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            if not re.match(email_regex, email):
                return {"message": "Invalid email format. Please enter a valid email address."}

        # Check for duplicate PAN
        if pan_number:
            duplicate_pan = http.request.env['company.register'].sudo().search([("pan_number", "=", pan_number)])
            if duplicate_pan:
                return {"message": f"The PAN number '{pan_number}' already exists. Each PAN number must be unique."}

        # Check for duplicate Mobile
        if mobile:
            duplicate_mobile = http.request.env['company.register'].sudo().search([("mobile", "=", mobile)])
            if duplicate_mobile:
                return {"message": f"The mobile number '{mobile}' already exists. Each mobile number must be unique."}

        # Check for duplicate Email
        if email:
            duplicate_email = http.request.env['company.register'].sudo().search([("email", "=", email)])
            if duplicate_email:
                return {"message": f"The email address '{email}' already exists. Each email address must be unique."}

        # Check for duplicate Organization Name
        if name:
            duplicate_name = http.request.env['company.register'].sudo().search([("organization_name_en", "=", name)])
            if duplicate_name:
                return {"message": f"The organization name '{name}' already exists."}

        return None
    @http.route("/trading/api/company_register/create", type="http",auth='public',cors="*", methods=["POST"], csrf=False)
    def create_company(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received request from: {hosturl}")

            company_id = 1
            company = None
            if company_id:
                company = request.env['res.company'].sudo().search([('id', '=', int(company_id))], limit=1)
                if not company:
                    return http.Response(
                        status=404,
                        response=json.dumps({
                            "status": "fail", 
                            "data":{
                                "message": "Company not found"
                            }}),
                        content_type="application/json"
                    )
         
            company_type = kw.get('company_type')
            organization_name_en = kw.get('organization_name_en')
            organization_name_np = kw.get('organization_name_np')
            organization_type = kw.get('organization_type')
            fiscal_year = kw.get('fiscal_year')
            first_name_en = kw.get('first_name_en')
            middle_name_en = kw.get('middle_name_en')
            last_name_en = kw.get('last_name_en')
            first_name_np = kw.get('first_name_np')
            middle_name_np = kw.get('middle_name_np')
            last_name_np = kw.get('last_name_np')
            owner_citizenship_front = kw.get('owner_citizenship_front')
            owner_citizenship_back = kw.get('owner_citizenship_back') 
            owner_name_en = kw.get('owner_name_en')
            owner_name_np = kw.get('owner_name_np')
            company_docs = kw.get('company_documents')
            gender = kw.get('gender')
            pan_number = kw.get('pan_number') 
            phone = kw.get('phone') 
            mobile = kw.get('mobile')
            email =  kw.get('email') 
            province =kw.get('province') 
            district =kw.get('district')
            palika = kw.get('palika') 
            ward_no =kw.get('ward_no')
            registration_no = kw.get('registration_no')
            tax_id = kw.get('tax_id')
            login_bg_img_company = kw.get('login_bg_img_company')
            login_pp_individual = kw.get('login_pp_individual')
            fiscal_year = kw.get('fiscal_year_id')
            currency_id = kw.get('currency_id')
            address_latitude=kw.get('address_latitude')
            address_longitude=kw.get('address_longitude')
            pickup_location=kw.get('pickup_location')
            pricing = kw.get('pricing')
            
            validation_error = self.validate_company_data(company_type, pan_number, mobile, email, organization_name_en)
            if validation_error:
                return http.Response(
                    status=401,
                    response=json.dumps({"status": "fail", "data": validation_error}),
                    content_type='application/json'
                )

            update_vals_company = {}
            if (company_type == 'individual'):
                if not (((first_name_en and last_name_en) or middle_name_en) or ((first_name_np and last_name_np) or middle_name_np)):
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status":"fail",
                            "data":{
                                "message": "Personal name is required"
                            }}),
                        content_type='application/json'
                    )
                
                if not gender:
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status":"fail",
                            "data":{
                                "message": "Gender is required"
                            }}),
                        content_type='application/json'
                    )
                
                if not (pan_number and email and mobile and province and district and palika and ward_no):
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status": "fail",
                            "data": {
                                "message": "At least one of the required fields (PAN number,email,mobile,province,district and ward_no) must be provided"
                            }
                        }),
                        content_type='application/json'
                    )
            
            if (company_type == 'organization'):
                if not (organization_name_en or organization_name_np):
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status":"fail",
                            "data":{
                                "message": "Organization name is required"
                            }}),
                        content_type='application/json'
                    )
                
                if not organization_type:
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status":"fail",
                            "data":{
                                "message": "Organization type is required"
                            }}),
                        content_type='application/json'
                    )
                
                if not (registration_no and tax_id):
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status": "fail",
                            "data": {
                                "message": "Registration number and tax ID are required for organization type"
                            }
                        }),
                        content_type='application/json'
                    )
            
                if not (pan_number and email and mobile and province and district and palika and ward_no):
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status": "fail",
                            "data": {
                                "message": "At least one of the required fields (PAN number,email,mobile,province,district and ward_no) must be provided"
                            }
                        }),
                        content_type='application/json'
                    )
                  
            if login_bg_img_company:
                if login_bg_img_company == 'null':
                    login_bg_img_binary_company = None
                else:
                    login_bg_img_binary_company = base64.b64encode(login_bg_img_company.read())
            else:
                login_bg_img_binary_company = None

            if login_pp_individual:
                if login_pp_individual == 'null':
                    login_bg_img_binary_individual = None
                else:
                    login_bg_img_binary_individual = base64.b64encode(login_pp_individual.read())
            else:
                login_bg_img_binary_individual = None

            if owner_citizenship_front:
                if owner_citizenship_front == 'null':
                    owner_citizenship_front_binary = None
                else:
                    owner_citizenship_front_binary = base64.b64encode(owner_citizenship_front.read())
            else:
                owner_citizenship_front_binary = None

            if owner_citizenship_back:
                if owner_citizenship_back == 'null':
                    owner_citizenship_back_binary = None
                else:
                    owner_citizenship_back_binary = base64.b64encode(owner_citizenship_back.read())
            else:
                owner_citizenship_back_binary = None
            
            if 'company_category_ids' in kw:
                try:
                    category_ids = json.loads(kw.get('company_category_ids','[]'))
                    if isinstance(category_ids, list):
                        category_ids = [int(id) for id in category_ids if id.isdigit()]
                        update_vals_company['company_category_ids'] = [(6, 0, category_ids)]
                    else:
                        update_vals_company['company_category_ids'] = None 
                        return http.Response(
                            status=400,
                            response=json.dumps({
                                "status": "fail",
                                "data": {
                                    "message": "company_category_ids is not a list"
                                }
                            }),
                            content_type='application/json'
                        )
                except json.JSONDecodeError:
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status": "fail",
                            "data": {
                                "message": "company_category_ids is required"
                            }
                        }),
                        content_type='application/json'
                    )
            else:
                update_vals_company['company_category_ids'] = None  

            company_docs_ids = []
            form = request.httprequest.form
            files = request.httprequest.files
            for key in files:
                if key.startswith('company_docs'):
                    index = key.split('[')[1].split(']')[0]
                    document_type = form.get(f'company_docs[{index}][document_type]')
                    document_file = files.get(key)
                    if document_file:
                        document_content_binary = base64.b64encode(document_file.read()).decode('utf-8')
                        doc_vals = {
                            'type_id': document_type,
                            'documents': document_content_binary,
                            'file_name': document_file.filename,
                        }
                        company_docs_ids.append((0, 0, doc_vals))
            
            if not company_docs_ids:
                company_docs_ids = None

    
            if (company_type == 'organization'):
                company_vals = request.env['company.register'].sudo().create({
                    'company_type':company_type,
                    'organization_name_en': organization_name_en,
                    'organization_name_np': organization_name_np,
                    'owner_name_en': owner_name_en,
                    'owner_name_np': owner_name_np,
                    'organization_type': organization_type,
                    'fiscal_year': fiscal_year,
                    'company_category_ids': update_vals_company.get('company_category_ids', []),
                    # 'company_category_product_ids':  update_vals_company.get('company_category_product_ids', []),
                    'pan_number': pan_number,
                    'phone': phone,
                    'mobile': mobile,
                    'email': email,
                    'province': province,
                    'district': district,
                    'palika': palika,
                    'ward_no': ward_no,
                    'registration_no': registration_no,
                    'tax_id': tax_id,
                    'login_bg_img_company':login_bg_img_binary_company,
                    'owner_citizenship_front' : owner_citizenship_front_binary,
                    'owner_citizenship_back' : owner_citizenship_back_binary,
                    'registration_docs_ids': company_docs_ids,
                    'ref_id': company.id if company_id else None,
                    'requested_by': company.name if company_id else None,
                    'currency_id': currency_id,
                    'latitude':address_latitude,
                    'longitude':address_longitude,
                    'pickup_location':pickup_location,
                    'pricing': pricing,
                    
                })
            elif (company_type == 'individual'):
                company_vals = request.env['company.register'].sudo().create({
                    'company_type':company_type,
                    'fiscal_year': fiscal_year,
                    'first_name_en': first_name_en,
                    'middle_name_en': middle_name_en,
                    'last_name_en': last_name_en,
                    'first_name_np': first_name_np,
                    'middle_name_np': middle_name_np,
                    'last_name_np': last_name_np,
                    'company_category_ids': update_vals_company.get('company_category_ids', []),
                    # 'company_category_product_ids':  update_vals_company.get('company_category_product_ids', []),
                    'pan_number': pan_number,
                    'gender': gender,
                    'phone': phone,
                    'mobile': mobile,
                    'email': email,
                    'province': province,
                    'district': district,
                    'palika': palika,
                    'ward_no': ward_no,
                    'registration_no': registration_no,
                    'tax_id': tax_id,
                    'login_bg_img_individual':login_bg_img_binary_individual,
                    'owner_citizenship_front' : owner_citizenship_front_binary,
                    'owner_citizenship_back' : owner_citizenship_back_binary,
                    'registration_docs_ids': company_docs_ids,
                    'ref_id': company.id if company_id else None,
                    'requested_by': company.name if company_id else None,
                    'fiscal_year': fiscal_year,
                    'currency_id': currency_id,
                    'latitude':address_latitude,
                    'longitude':address_longitude,
                    'pickup_location':pickup_location,
                    'pricing': pricing,
                })

            if company_vals:
                if (company_type=='organization'):
                    return http.Response(
                        response=json.dumps({
                            "status":"success",
                            "data":{
                                "message": f"Company {organization_name_en} registered successfully",
                                "company_id": company_vals.id
                            }}),
                        content_type='application/json'
                        )     
                elif (company_type=='individual'):
                    return http.Response(
                        response=json.dumps({
                            "status":"success",
                            "data":{
                                "message": f"Personal account for {first_name_en} registered successfully",
                                "data": company_vals.id
                            }}),
                        content_type='application/json'
                        )    
                
        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
            
    @http.route("/trading/api/company_register/update", type="http", auth='public', cors="*", methods=["PUT"], csrf=False)
    def update_company(self, **kw):
            try:
                company_id = kw.get('company_id')
                if not company_id:
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status": "fail",
                            "data": {
                                "message": "company_id is required for updating"
                            }
                        }),
                        content_type="application/json"
                    )

                company = request.env['company.register'].sudo().search([('id', '=', int(company_id))], limit=1)
                if not company:
                    return http.Response(
                        status=404,
                        response=json.dumps({
                            "status": "fail",
                            "data": {
                                "message": "Company not found"
                            }
                        }),
                        content_type="application/json"
                    )

                # Process the same fields as in POST request
                company_type = kw.get('company_type')
                organization_name_en = kw.get('organization_name_en')
                organization_name_np = kw.get('organization_name_np')
                organization_type = kw.get('organization_type')
                first_name_en = kw.get('first_name_en')
                middle_name_en = kw.get('middle_name_en')
                last_name_en = kw.get('last_name_en')
                first_name_np = kw.get('first_name_np')
                middle_name_np = kw.get('middle_name_np')
                last_name_np = kw.get('last_name_np')
                owner_citizenship_front = kw.get('owner_citizenship_front')
                owner_citizenship_back = kw.get('owner_citizenship_back') 
                company_docs = kw.get('company_documents')
                gender = kw.get('gender')
                pan_number = kw.get('pan_number') 
                phone = kw.get('phone') 
                mobile = kw.get('mobile')
                email =  kw.get('email') 
                province = kw.get('province') 
                district = kw.get('district')
                palika = kw.get('palika') 
                ward_no = kw.get('ward_no')
                registration_no = kw.get('registration_no')
                tax_id = kw.get('tax_id')
                login_bg_img_company = kw.get('login_bg_img_company')
                login_pp_individual = kw.get('login_pp_individual')
                pricing = kw.get('pricing')

                # Handling file fields and binary conversion
                if login_bg_img_company:
                    if login_bg_img_company == 'null':
                        login_bg_img_binary_company = None
                    else:
                        login_bg_img_binary_company = base64.b64encode(login_bg_img_company.read())
                else:
                    login_bg_img_binary_company = None

                if login_pp_individual:
                    if login_pp_individual == 'null':
                        login_bg_img_binary_individual = None
                    else:
                        login_bg_img_binary_individual = base64.b64encode(login_pp_individual.read())
                else:
                    login_bg_img_binary_individual = None

                if owner_citizenship_front:
                    if owner_citizenship_front == 'null':
                        owner_citizenship_front_binary = None
                    else:
                        owner_citizenship_front_binary = base64.b64encode(owner_citizenship_front.read())
                else:
                    owner_citizenship_front_binary = None

                if owner_citizenship_back:
                    if owner_citizenship_back == 'null':
                        owner_citizenship_back_binary = None
                    else:
                        owner_citizenship_back_binary = base64.b64encode(owner_citizenship_back.read())
                else:
                    owner_citizenship_back_binary = None

                # Process company documents similarly to the POST method
                company_docs_ids = []
                form = request.httprequest.form
                files = request.httprequest.files
                for key in files:
                    if key.startswith('company_docs'):
                        index = key.split('[')[1].split(']')[0]
                        document_type = form.get(f'company_docs[{index}][document_type]')
                        document_file = files.get(key)
                        
                        if document_file:
                            document_content_binary = base64.b64encode(document_file.read()).decode('utf-8')
                            doc_vals = {
                                'type_id': document_type,
                                'documents': document_content_binary,
                            }
                            company_docs_ids.append((0, 0, doc_vals))


                # Updating company record in the database
                update_vals = {}

                if company.company_type == 'organization':
                    # Only add fields to update_vals if they have values
                    if organization_name_en:
                        update_vals['organization_name_en'] = organization_name_en
                    if organization_name_np:
                        update_vals['organization_name_np'] = organization_name_np
                    if organization_type:
                        update_vals['organization_type'] = organization_type
                    if pan_number:
                        update_vals['pan_number'] = pan_number
                    if phone:
                        update_vals['phone'] = phone
                    if mobile:
                        update_vals['mobile'] = mobile
                    if email:
                        update_vals['email'] = email
                    if province:
                        update_vals['province'] = province
                    if district:
                        update_vals['district'] = district
                    if palika:
                        update_vals['palika'] = palika
                    if ward_no:
                        update_vals['ward_no'] = ward_no
                    if registration_no:
                        update_vals['registration_no'] = registration_no
                    if tax_id:
                        update_vals['tax_id'] = tax_id
                    if login_bg_img_binary_company:
                        update_vals['login_bg_img_company'] = login_bg_img_binary_company
                    if owner_citizenship_front_binary:
                        update_vals['owner_citizenship_front'] = owner_citizenship_front_binary
                    if owner_citizenship_back_binary:
                        update_vals['owner_citizenship_back'] = owner_citizenship_back_binary
                    if company_docs_ids:
                        update_vals['registration_docs_ids'] = company_docs_ids
                    if pricing:
                        update_vals['pricing'] = pricing

                elif company.company_type == 'individual':
                    # Only add fields to update_vals if they have values
                    if first_name_en:
                        update_vals['first_name_en'] = first_name_en
                    if middle_name_en:
                        update_vals['middle_name_en'] = middle_name_en
                    if last_name_en:
                        update_vals['last_name_en'] = last_name_en
                    if first_name_np:
                        update_vals['first_name_np'] = first_name_np
                    if middle_name_np:
                        update_vals['middle_name_np'] = middle_name_np
                    if last_name_np:
                        update_vals['last_name_np'] = last_name_np
                    if pan_number:
                        update_vals['pan_number'] = pan_number
                    if phone:
                        update_vals['phone'] = phone
                    if mobile:
                        update_vals['mobile'] = mobile
                    if email:
                        update_vals['email'] = email
                    if province:
                        update_vals['province'] = province
                    if district:
                        update_vals['district'] = district
                    if palika:
                        update_vals['palika'] = palika
                    if ward_no:
                        update_vals['ward_no'] = ward_no
                    if login_bg_img_binary_individual:
                        update_vals['login_bg_img_individual'] = login_bg_img_binary_individual
                    if owner_citizenship_front_binary:
                        update_vals['owner_citizenship_front'] = owner_citizenship_front_binary
                    if owner_citizenship_back_binary:
                        update_vals['owner_citizenship_back'] = owner_citizenship_back_binary
                    if company_docs_ids:
                        update_vals['registration_docs_ids'] = company_docs_ids
                    if pricing:
                        update_vals['pricing'] = pricing

                # Only call write if there are values to update
                print("update_vals",update_vals)
                if update_vals:
                    update_vals['state'] = "resubmit"
                    company.sudo().write(update_vals)
                return http.Response(
                    status=200,
                    response=json.dumps({
                        "status": "success",
                        "data": {
                            "message": f"Company updated successfully",
                            "company_id": company.id
                        }
                    }),
                    content_type="application/json"
                )

            except Exception as e:
                _logger.error(f"Error: {str(e)}")
                return http.Response(
                    status=500,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": str(e)
                        }
                    }),
                    content_type="application/json"
                )

    @http.route("/trading/api/add_users", type="http",auth='public',cors="*", methods=["POST"], csrf=False)
    def add_user(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received request from: {hosturl}")

            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)

            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[
                        ('Content-Type', 'application/json')
                    ],
                    status=status_code
                )

            company_id = kw.get('company_id')
            if not company_id:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": "company_id Required"
                        }}),
                    content_type='application/json'
                )

            company = request.env['res.company'].sudo().search([('id', '=', int(company_id))], limit=1)
            if not company:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": "Company not found"
                        }}),
                    content_type='application/json'
                )

            user_name = kw.get('user_name')
            name_np = kw.get('user_name_np')
            user_email = kw.get('user_email')
            password = kw.get('password')
            profile_pic = kw.get('profile_pic')
            if profile_pic:
                if profile_pic == 'null':
                    profile_pic_binary = None
                else:
                    profile_pic_binary = base64.b64encode(profile_pic.read())
            else:
                profile_pic_binary = None

            sales_role = kw.get('sales_role')
            accounting_role = kw.get('accounting_role')
            inventory_role = kw.get('inventory_role')
            purchase_role = kw.get('purchase_role')
            trade_role = kw.get('trade_access')

            print("testing",purchase_role)
            print(type(purchase_role))

            groups = []
            # if trade_role == '0':
            #     trade_group = request.env.ref('farmer.group_trade_user_access').id
            #     groups.append(trade_group)
            # elif trade_role == '1':
            #     trade_group = request.env.ref('farmer.group_trade_admin_access').id
            #     groups.append(trade_group)

            if sales_role == '0':
                sales_group = request.env.ref('sales_team.group_sale_salesman').id
                groups.append(sales_group)
            elif sales_role == '1':
                sales_group = request.env.ref('sales_team.group_sale_manager').id
                groups.append(sales_group)
            
            if accounting_role == '0':
                account_group = request.env.ref('account.group_account_user').id
                groups.append(account_group)
            elif accounting_role == '1':
                account_group = request.env.ref('account.group_account_manager').id
                groups.append(account_group)

            if inventory_role == '0':
                stock_group = request.env.ref('stock.group_stock_user').id
                groups.append(stock_group)
            elif inventory_role == '1':
                stock_group = request.env.ref('stock.group_stock_manager').id
                groups.append(stock_group)

            if purchase_role == '0':
                purchase_group = request.env.ref('purchase.group_purchase_user').id
                groups.append(purchase_group)
            elif purchase_role == '1':
                purchase_group = request.env.ref('purchase.group_purchase_manager').id
                groups.append(purchase_group) 

            print(groups)

            users = request.env['res.users'].sudo().create({
                'name':user_name,
                'name_np':name_np,
                'login': user_email,
                'company_id': company.id,
                'company_ids': [(4, company.id)],
                'image_1920':profile_pic_binary,
                'groups_id': [(6, 0, groups)], 
            })
               
            if not users:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": f"User creation fail"
                        }}),
                    content_type='application/json'
                )
          
            users.sudo().write({'password': password})
            return http.Response(
                    status=200,
                    response=json.dumps({
                        "status":"success",
                        "data":{
                            "message": f"User '{users.name}' created successfuly for company{company.name}"
                        }}),
                    content_type='application/json'
                )


        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
































class UserRegistration(http.Controller):
    def get_document_link(self,doc):
        if not doc.file_name:
            return None  # Skip if no filename

        file_extension = doc.file_name.split('.')[-1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            return None  # Skip if the extension is not allowed

        base_url = "http://lekhaplus.com/web"
        if file_extension == "pdf":
            return f"{base_url}/content?model=registration.documents&id={doc.id}&field=documents&filename={doc.file_name}"
        else:
            return f"{base_url}/image?model=registration.documents&id={doc.id}&field=documents&filename={doc.file_name}"
        
    @http.route("/trading/api/user_register", type="http",auth='public',cors="*", methods=["POST"], csrf=False)
    def create_company(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received request from: {hosturl}")

    
            name = kw.get('name')
            if not name:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": "User name is required"
                        }}),
                    content_type='application/json'
                )
            
            _logger.info(f"Received request from: {name}")
            name_np = kw.get('name_np')
         
            citizenship_front = kw.get('citizenship_front')
            if citizenship_front:
                if citizenship_front == 'null':
                    citizenship_front_binary = None
                else:
                    citizenship_front_binary = base64.b64encode(citizenship_front.read())
            else:
                citizenship_front_binary = None

            citizenship_back = kw.get('citizenship_back') 
            if citizenship_back:
                if citizenship_back == 'null':
                    citizenship_back_binary = None
                else:
                    citizenship_back_binary = base64.b64encode(citizenship_front.read())
            else:
               citizenship_back_binary = None 
         
            national_id_pic = kw.get('national_id_pic')
            if national_id_pic:
                if national_id_pic == 'null':
                    national_id_pic_binary = None
                else:
                    national_id_pic_binary = base64.b64encode(national_id_pic.read())
            else:
                national_id_pic_binary = None

            contact = kw.get('contact')
            address = kw.get('address')
            pan_number = kw.get('pan_vat') 
            bank_details_id = kw.get('bank_details_id')
            branch_name_id = kw.get('branch_name_id')
            account_no = kw.get('account_no')
 
            email =  kw.get('email')
            wallet_no = kw.get('wallet_no')
            wallet_type = kw.get('wallet_type')
#             # province =kw.get('province')
#             # district =kw.get('district')
#             # ward_no =kw.get('ward_no')
#             # user_img = kw.get('user_profile')

            bank_details = request.env['bank.details'].sudo().browse(bank_details_id)

            branch_name = request.env['branch.bank'].sudo().browse(branch_name_id)


            update_vals_company = {}
            if 'company_category_ids' in kw:
                try:
                    category_ids = json.loads(kw.get('company_category_ids'))
                    if isinstance(category_ids, list):
                        category_ids = [int(id) for id in category_ids if id.isdigit()]
                        update_vals_company['business_category'] = [(6, 0, category_ids)]
                    else:
                        update_vals_company['business_category'] = None 
                        return http.Response(
                            status=400,
                            response=json.dumps({
                                "status": "error",
                                "data": {
                                    "message": "company_category_ids is not a list"
                                }
                            }),
                            content_type='application/json'
                        )
                except json.JSONDecodeError:
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status": "error",
                            "data": {
                                "message": "Failed to decode company_category_ids"
                            }
                        }),
                        content_type='application/json'
                    )
            else:
                update_vals_company['company_category_ids'] = None  

            if 'company_category_product_ids' in kw:
                try:
                    filtered_product_ids = json.loads(kw.get('company_category_product_ids')) 
                    if isinstance(filtered_product_ids, list):
                        products = request.env['product.product'].sudo().search([('id', 'in', filtered_product_ids)])
                        filtered_product_ids = [int(id) for id in filtered_product_ids if id.isdigit()]
                        product_names = products.mapped('name')
                        _logger.info(f"Product names corresponding to IDs {filtered_product_ids}: {product_names}")

                        update_vals_company['product_category'] = [(6, 0, filtered_product_ids)]
                    else:
                        update_vals_company['product_category'] = None
                except json.JSONDecodeError:
                    update_vals_company['product_category'] = None
            else:
                update_vals_company['product_category'] = None

            users = request.env['user.registration'].sudo().create({
                'name': name,
                'name_np': name_np,
                'business_category': update_vals_company.get('business_category', []),
                'product_category':  update_vals_company.get('product_category', []),
                'pan_vat': pan_number,
                'contact': contact,
                'email': email,
                'address': address,
                'bank_details': bank_details.id,
                'branch_name': branch_name.id,
                'account_no' : kw.get('account_no'),
                # 'province': province,
                # 'district': district,
                # 'ward_no': ward_no,
                # 'login_bg_img':login_bg_img,
                'national_id' : kw.get('national_id'),
                'citizenship_no' : kw.get('citizenship_no'),
                'citizenship_front' : citizenship_front_binary,
                'citizenship_back' : citizenship_back_binary,
                'national_id_pic':national_id_pic_binary,
                'wallet_no': wallet_no,
                'wallet_type': wallet_type
          
            })

            return request.make_response(
                json.dumps({
                    "status": "success",
                    "data" : {
                        "message": f"Users {name} register successfully",
                        "users_id":users.id
                        }
                    }),
                headers=[("Content-Type", "application/json")]
            )
            
        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
            

    @http.route("/trading/api/edit_users", type="http",auth='public',cors="*", methods=["PUT"], csrf=False)
    def edit_users(self, **kw):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received request from: {hosturl}")

            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[
                        ('Content-Type', 'application/json')
                    ],
                    status=status_code
                )
            
            
            user_id = kw.get('user_id')
            _logger.info(f"Received request from: {user_id}")
            if not user_id:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": "user_id is required"
                        }}),
                    content_type='application/json'
                )
            
            users = request.env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
            if not users:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": "Users not found"
                        }}),
                    content_type='application/json'
                )
            

            company = request.env['res.company'].sudo().search([('id', '=', int(users.company_id))], limit=1)
            # if not company:
            #     return http.Response(
            #         status=404,
            #         response=json.dumps({"status": "error", "message": "Company not found"}),
            #         content_type="application/json"
            #     )
            _logger.info(f"Received request from: {company.name}")
#      

            update_vals = {}
            update_vals_company = {}
            if 'name' in kw:
                update_vals['name'] = kw.get('name')
            if 'name_np' in kw:
                update_vals['name_np'] = kw.get('name_np')
            if 'pan_vat' in kw:
                update_vals['pan_vat'] = kw.get('pan_vat')
            if 'contact' in kw:
                update_vals['contact'] = kw.get('phone')
#             if 'mobile' in kw:
#                 update_vals['mobile'] = kw.get('mobile')
            if 'email' in kw:
                update_vals['email'] = kw.get('email')
#             if 'street' in kw:
#                 update_vals['street'] = kw.get('street')
#             if 'province' in kw:
#                 update_vals['province'] = kw.get('province')
#             if 'district' in kw:
#                 update_vals['district'] = kw.get('district')
#             if 'ward_no' in kw:
#                 update_vals['ward_no'] = kw.get('ward_no')
            if 'image_1920' in kw:
                update_vals['image_1920'] = kw.get('image_1920')

            old_password = kw.get('old_password')
            new_password = kw.get('new_password')

            print("user_id",users)
            if old_password and new_password:
                result = request.env['res.users'].validate_and_change_password(old_password, new_password,user_id)
                if result:
                    update_vals['password'] = new_password
                else:
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status": "fail",
                            "data": {
                                "message": "Old password is not a matched"
                            }
                        }),
                        content_type='application/json'
                    )

         
               
            if 'company_category_ids' in kw:
                try:
                    category_ids = json.loads(kw.get('company_category_ids'))
                    if isinstance(category_ids, list):
                        category_ids = [int(id) for id in category_ids if id.isdigit()]
                        update_vals_company['company_category'] = [(6, 0, category_ids)]

                    else:
                        update_vals_company['company_category'] = None 
                        return http.Response(
                            status=400,
                            response=json.dumps({
                                "status": "fail",
                                "data": {
                                    "message": "company_category_ids is not a list"
                                }
                            }),
                            content_type='application/json'
                        )
                except json.JSONDecodeError:
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status": "error",
                            "data": {
                                "message": "Failed to decode company_category_ids"
                            }
                        }),
                        content_type='application/json'
                    )
            else:
                update_vals_company['company_category'] = None 

            if 'company_category_product_ids' in kw:
                try:
                    filtered_product_ids = json.loads(kw.get('company_category_product_ids'))
                    if isinstance(filtered_product_ids, list):

                        filtered_product_ids = [int(id) for id in filtered_product_ids if id.isdigit()]
                        products = request.env['product.product'].sudo().search([('id', 'in', filtered_product_ids)])

                        product_names = products.mapped('name')
                        _logger.info(f"Product names corresponding to IDs {filtered_product_ids}: {product_names}")

                        update_vals_company['company_category_product'] = [(6, 0, filtered_product_ids)]
                    else:
                        update_vals_company['company_category_product'] = None
                except json.JSONDecodeError:
                    update_vals_company['company_category_product'] = None
            else:
                update_vals_company['company_category_product'] = None

            if update_vals_company:
                company.sudo().write(update_vals_company)

            if update_vals:
                users.sudo().write(update_vals)
      

            return http.Response(
                status=200,
                response =json.dumps({
                    "status": "success", 
                    "data":{
                        "message": f"Users '{users.name}' updated successfully"
                    }
                    }),
                content_type='application/json'
            )

        except Exception as e:
            return http.Response(
                status=500,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }
                }),
                content_type="application/json"
            )

    @http.route("/trading/api/company_details/get", type="http", auth="public", cors="*", methods=["GET"])
    def get_company(self, **kw):
        try:
            company_id = kw.get('id')
            update_code = kw.get('update_code')
            domain=[]
            if company_id:
                domain = [('id', '=', int(company_id))] if company_id else []
            if update_code:
                domain = [('update_code', '=', update_code)] if update_code else []
            
            companies = request.env['company.register'].sudo().search(domain)

            if not companies:
                return http.Response(
                    status=404,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Company not found" if company_id else "No companies available"
                        }
                    }),
                    content_type='application/json'
                )

            company_data_list = []
            for company in companies:
                company_data = {
                    'company_id': company.id or None,
                    'company_type': company.company_type or None,
                    'currency_id': company.currency_id.id if company.currency_id else None,
                    'company_category_ids': company.company_category_ids.ids if company.company_category_ids else None,
                    'company_category_names': company.company_category_ids.mapped('name') if company.company_category_ids else None,
                    'latitude': company.latitude or None,
                    'longitude': company.longitude or None,
                    'pricing': company.pricing or None,
                }

                if company.company_type == 'organization':
                    company_data.update({
                        'organization_name_en': company.organization_name_en or None,
                        'organization_name_np': company.organization_name_np or None,
                        'owner_name_en': company.owner_name_en or None,
                        'owner_name_np': company.owner_name_np or None,
                        'organization_type': company.organization_type or None,
                        'fiscal_year': company.fiscal_year.id if company.fiscal_year else None,
                        'pan_number': company.pan_number or None,
                        'phone': company.phone or None,
                        'mobile': company.mobile or None,
                        'email': company.email or None,
                        'province': company.province.id if company.province else None,
                        'district': company.district.id if company.district else None,
                        'palika': company.palika.id if company.palika else None,
                        'province_name': company.province.name if company.province else None,
                        'district_name': company.district.district_name if company.district else None,
                        'palika_name': company.palika.palika_name if company.palika else None,
                        'ward_no': company.ward_no or None,
                        'registration_no': company.registration_no or None,
                        'tax_id': company.tax_id or None,
                        'state': company.state or None,
                        'owner_citizenship_front': f"http://lekhaplus.com/web/image?model=company.register&id={company.id}&field=owner_citizenship_front" if company.owner_citizenship_front else None,
                        'owner_citizenship_back': f"http://lekhaplus.com/web/image?model=company.register&id={company.id}&field=owner_citizenship_back" if company.owner_citizenship_back else None,
                        'login_bg_img_company': f"http://lekhaplus.com/web/image?model=company.register&id={company.id}&field=login_bg_img_company" if company.login_bg_img_company else None,
                        'registration_docs_ids': [
                            {
                                'document_type': doc.type_id.id if doc.type_id else None,
                                'document_link': self.get_document_link(doc),
                                'file_name': doc.file_name or None,
                            } 
                            for doc in company.registration_docs_ids if self.get_document_link(doc)
                        ] if company.registration_docs_ids else None,
                    })

                elif company.company_type == 'individual':
                    company_data.update({
                        'fiscal_year': company.fiscal_year.id if company.fiscal_year else None,
                        'first_name_en': company.first_name_en or None,
                        'middle_name_en': company.middle_name_en or None,
                        'last_name_en': company.last_name_en or None,
                        'first_name_np': company.first_name_np or None,
                        'middle_name_np': company.middle_name_np or None,
                        'last_name_np': company.last_name_np or None,
                        'pan_number': company.pan_number or None,
                        'phone': company.phone or None,
                        'mobile': company.mobile or None,
                        'email': company.email or None,
                        'gender': company.gender or None,
                        'province': company.province.id if company.province else None,
                        'district': company.district.id if company.district else None,
                        'palika': company.palika.id if company.palika else None,
                        'province_name': company.province.name if company.province else None,
                        'district_name': company.district.district_name if company.district else None,
                        'palika_name': company.palika.palika_name if company.palika else None,
                        'ward_no': company.ward_no or None, 
                        'registration_no': company.registration_no or None,
                        'tax_id': company.tax_id or None,
                        'state': company.state or None,
                        'ref_company': company.create_uid.company_id.id if company else False,
                        'login_bg_img_individual': f"http://lekhaplus.com/web/image?model=company.register&id={company.id}&field=login_bg_img_individual" if company.login_bg_img_individual else None,
                        'owner_citizenship_front': f"http://lekhaplus.com/web/image?model=company.register&id={company.id}&field=owner_citizenship_front" if company.owner_citizenship_front else None,
                        'owner_citizenship_back': f"http://lekhaplus.com/web/image?model=company.register&id={company.id}&field=owner_citizenship_back" if company.owner_citizenship_back else None,
                        'registration_docs_ids': [
                            {
                                'document_type': doc.type_id.id if doc.type_id else None,
                                'document_link': self.get_document_link(doc),
                                'file_name': doc.file_name or None,
                            } 
                            for doc in company.registration_docs_ids if self.get_document_link(doc)
                        ] if company.registration_docs_ids else None,
                                                
                                                })

                company_data_list.append(company_data)

            return http.Response(
                response=json.dumps({
                    "status": "success",
                    "data": company_data_list if not (company_id or update_code) else company_data_list[0]
                }),
                content_type='application/json'
            )

        except Exception as e:
            return http.Response(
                status=500,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }
                }),
                content_type='application/json'
            )
    
    @http.route("/trading/api/company_details/approve_registration", type="http",csrf=False, auth="public", cors="*", methods=["POST"])
    def approve_registration(self, **kwargs):
        auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
        if auth_status['status'] == 'fail':
            return request.make_response(
                json.dumps(auth_status),
                headers=[('Content-Type', 'application/json')],
                status=status_code
            )
        raw_data = request.httprequest.data
        json_data = json.loads(raw_data)
        company_id = json_data.get("id")
        default_subject = json_data.get("default_subject", "Thank you for registering with us. We are excited to have you on board.")

        if not company_id:
            return http.Response(
                status=400,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": "Registration ID is required"
                    }
                }),
                content_type='application/json'
            )

        company = request.env['company.register'].sudo().search([('id', '=', company_id)], limit=1)
        if not company:
            return http.Response(
                status=404,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": "Registration Record not found"
                    }
                }),
                content_type='application/json'
            )

        # Pass all required fields in the context
        context_values = {
            "action": company.company_type,
            "email": company.email,
            "phone": company.phone,
            "mobile": company.mobile,
            "pan_number": company.pan_number,
            "organization_name_en": company.organization_name_en,
            "organization_name_np": company.organization_name_np,
            "tax_id": company.tax_id,
            "start_date": company.start_date,
            "recent_tax_paid_year": company.recent_tax_paid_year,
            "owner_name_np": company.owner_name_np,
            "owner_name_en": company.owner_name_en,
            "registration_no": company.registration_no,
            "organization_type": company.organization_type,
            "login_bg_img_individual": company.login_bg_img_individual,
            "login_bg_img_company": company.login_bg_img_company,
            "owner_citizenship_front": company.owner_citizenship_front,
            "owner_citizenship_back": company.owner_citizenship_back,
            "province_id": company.province.id if company.province else False,
            "district_id": company.district.id if company.district else False,
            "palika_id": company.palika.id if company.palika else False,
            "ward_no": company.ward_no,
            "pickup_location": company.pickup_location,
            "latitude": company.latitude,
            "longitude": company.longitude,
            "fiscal_year": company.fiscal_year,
            "company_category_ids": company.company_category_ids.ids,
            "company_docs_ids": company.registration_docs_ids.ids,
            "currency_id": company.currency_id.id if company.currency_id else False,
            "pricing": company.pricing,
            "first_name_en": company.first_name_en,
            "middle_name_en": company.middle_name_en,
            "last_name_en": company.last_name_en,
            "first_name_np": company.first_name_np,
            "middle_name_np": company.middle_name_np,
            "last_name_np": company.last_name_np,
        }


        # Create the email wizard
        email_wizard = request.env["email.wizard"].sudo().create({
            "company_register_id": company.id,
            "email_to": company.email,
            "subject": default_subject,
            "organization_name_en": company.organization_name_en,
            "owner_name_en": (
                f"{company.first_name_en} {company.middle_name_en} {company.last_name_en}"
                if company.company_type == "individual"
                else False
            ),
            "registration_docs_ids": [(6, 0, company.registration_docs_ids.ids)],
            "organization_type": company.organization_type,
            "category_ids": [(6, 0, company.company_category_ids.ids)],
            "is_organization": company.company_type == "organization",
            "is_reverted": False,
        })
        email_wizard.with_context(**context_values).action_send_email()
        return http.Response(
            status=200,
            response=json.dumps({
                "status": "success",
                "data": {
                    "message": "Registration approved and email sent successfully"
                }
            }),
            content_type='application/json'
        )
    @http.route("/trading/api/company_details/revert_registration", type="http",csrf=False, auth="public", cors="*", methods=["POST"])
    def revert_registration(self, **kwargs):
        auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
        if auth_status['status'] == 'fail':
            return request.make_response(
                json.dumps(auth_status),
                headers=[('Content-Type', 'application/json')],
                status=status_code
            )
        raw_data = request.httprequest.data
        json_data = json.loads(raw_data)
        company_id = json_data.get("id")
        default_subject = json_data.get("default_subject", "Reverted Notification")
        field_ids = json_data.get("field_ids", [])

        if not company_id:
            return http.Response(
                status=400,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": "Registration ID is required"
                    }
                }),
                content_type='application/json'
            )

        company = request.env['company.register'].sudo().search([('id', '=', company_id)], limit=1)
        if not company:
            return http.Response(
                status=404,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": "Registration Record not found"
                    }
                }),
                content_type='application/json'
            )
        if field_ids:
                try:
                    organization_ids = None
                    individual_ids = None
                    if isinstance(field_ids, list):
                        if company.company_type == 'organization':
                            organization_ids = [int(id) for id in field_ids if id.isdigit()]
                        else:
                            individual_ids = [int(id) for id in field_ids if id.isdigit()]
                    else:
                        return http.Response(
                            status=400,
                            response=json.dumps({
                                "status": "fail",
                                "data": {
                                    "message": "field_ids is not a list"
                                }
                            }),
                            content_type='application/json'
                        )
                except json.JSONDecodeError:
                    return http.Response(
                        status=400,
                        response=json.dumps({
                            "status": "fail",
                            "data": {
                                "message": "field_ids is required"
                            }
                        }),
                        content_type='application/json'
                    )

        # Pass all required fields in the context
        context_values = {
            "action": "reverted",
            "organization": company.company_type,
        }


        # Create the email wizard
        print("This is code ",company.update_code)
        email_wizard = request.env["email.wizard"].sudo().create({
            "company_register_id": company.id,
            "email_to": company.email,
            "subject": default_subject,
            "organization_name_en": company.organization_name_en,
            "owner_name_en": (
                f"{company.first_name_en} {company.middle_name_en} {company.last_name_en}"
                if company.company_type == "individual"
                else False
            ),
            "update_code":company.update_code,
            "organization_field_ids":[(6, 0,organization_ids)] if organization_ids else False,
            "individual_field_ids":[(6, 0, individual_ids)] if individual_ids else False,
            "is_reverted": False,
        })
        print("email wiz",email_wizard.update_code)
        email_wizard.with_context(**context_values).action_send_email()
        return http.Response(
            status=200,
            response=json.dumps({
                "status": "success",
                "data": {
                    "message": "Registration reverted and email sent successfully"
                }
            }),
            content_type='application/json'
        )
    @http.route("/trading/api/company_details/get_reverted_fields", type="http", csrf=False, auth="public", cors="*", methods=["GET"])
    def get_reverted_fields(self, **kwargs):
        auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
        if auth_status['status'] == 'fail':
            return request.make_response(
                json.dumps(auth_status),
                headers=[('Content-Type', 'application/json')],
                status=status_code
            )
        raw_data = request.httprequest.data
        json_data = json.loads(raw_data)
        company_id = json_data.get("id")

        if not company_id:
            return http.Response(
                status=400,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": "Registration ID is required"
                    }
                }),
                content_type='application/json'
            )

        company = request.env['company.register'].sudo().search([('id', '=', company_id)], limit=1)
        print("hereee", company.state)
        if company.state == "reverted":
            print("inside 1")
            wizard = request.env['email.wizard'].sudo().search([('company_register_id', '=', company.id)], limit=1, order='create_date desc')
            if wizard:
                if company.company_type == "individual":
                    fields = wizard.individual_field_ids
                else:
                    fields = wizard.organization_field_ids

                # Convert the fields to a serializable format
                field_data = []
                for field in fields:
                    field_data.append({
                        'id': field.id,
                        'name': field.name,
                        'field_code': field.field_code
                    })

                return http.Response(
                    status=200,
                    response=json.dumps({
                        "status": "success",
                        "data": field_data
                    }),
                    content_type='application/json'
                )

        return http.Response(
            status=400,
            response=json.dumps({
                "status": "fail",
                "data": {
                    "message": "Company is not in reverted state or no fields found."
                }
            }),
            content_type='application/json'
        )