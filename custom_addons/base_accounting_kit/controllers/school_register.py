from odoo.http import Response, request
from odoo import http,api,SUPERUSER_ID
import datetime
from datetime import date
import logging
import json
import base64
import re
from . import jwt_token_auth


_logger = logging.getLogger(__name__)

class SchoolRegistration(http.Controller):
    @http.route("/trading/api/create_school", type="http",auth='public',cors="*", methods=["POST"], csrf=False)
    def create_company(self, **kw):
        try:

            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            _logger.info(f"Received request from: {hosturl}")
            currency = request.env['res.currency'].sudo().search([('name', '=', 'NPR')])
         
   
            organization_name_en = kw.get('school_name_en')
            organization_name_np = kw.get('school_name_np')
            organization_type = kw.get('organization_type')
            fiscal_year = kw.get('fiscal_year_id')
       
            owner_citizenship_front = kw.get('owner_citizenship_front')
            owner_citizenship_back = kw.get('owner_citizenship_back') 
            company_docs = kw.get('company_documents')
            # parent_id = kw.get('parent_id')
            # parent = request.env['res.company'].sudo().search([('id', '=', parent_id)], limit=1)

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
       
            fiscal_year = kw.get('fiscal_year_id')
            currency_id = kw.get('currency_id')

            password = kw.get('password')
            username = kw.get('username')

            update_vals_company = {}

            print(f"ahhahahahahahaaaaahahahahah")
            print(f"email: {email}")
            print(f"pan_number: {pan_number}")
            print(f"phone: {phone}")
            # print(f"parent_id: {parent_id}")

            existing_partner = request.env['res.company'].search([('phone', '=', phone)], limit=1)
            if existing_partner:
                return Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "The phone number is already in use."
                        }
                    }),
                    content_type='application/json'
                )
            
            existing_email = request.env['res.company'].search([('email', '=', email)], limit=1)
            if existing_email:
                return Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "The email is already in use."
                        }
                    }),
                    content_type='application/json'
                )
            
            if pan_number and not re.match(r'^\d{9}$', pan_number):
                return Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "PAN number must be exactly 9 digits."
                        }
                    }),
                    content_type='application/json'
                )
            if phone and not re.match(r'^97\d{8}$|^98\d{8}$', phone):
                return Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Phone number must be 10 digits and start with 97 or 98."
                        }
                    }),
                    content_type='application/json'
                )
            
            if not (email):
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Ogranization email is required"
                        }
                    }),
                    content_type='application/json'
                )

            if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                return Response(
                    status=400,
                    response=json.dumps({
                        "status": "fail",
                        "data": {
                            "message": "Email must be a valid format."
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
                                    "message": "company_category is not a list"
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
                                "message": "company_category is required"
                            }
                        }),
                        content_type='application/json'
                    )
            else:
                update_vals_company['company_category'] = None  

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
            
            if not company_docs_ids:
                company_docs_ids = None
           
            company = request.env['res.company'].sudo().create({
                'name': organization_name_en,
                'name_np': organization_name_np,
                'organization_type': organization_type,
                'fiscal_year': fiscal_year,
                'company_category': update_vals_company.get('company_category', []),
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
                'login_bg_img':login_bg_img_binary_company,
                'owner_citizenship_front' : owner_citizenship_front_binary,
                'owner_citizenship_back' : owner_citizenship_back_binary,
                'company_docs_ids': company_docs_ids,
                'currency_id':117,
                'recent_tax_paid_year':kw.get('recent_tax_paid_year'),
                'parent_id':1,
            })
            user_data = {
                'name': kw.get('school_name_en'), 
                'name_np':kw.get('school_name_np'),
                'login': kw.get('username') if kw.get('username') else kw.get('email'),
                'company_ids': [(4, company.id)],
                'company_id':company.id,
                'email':email,
            }
            request.env['res.users'].sudo().create(user_data)

            users = request.env['res.users'].sudo().search([('company_id', '=', company.id)])
            for user in users:
                user.write({
                    'password': password,
                    'login': username if username else email,
                    # 'company_ids': [(4, company.id)],
                })
            if users:
                return http.Response(
                    response=json.dumps({
                        "status":"success",
                        "data":{
                            "message": f"Company {organization_name_en} Created successfully",
                            "company_id": company.id,
                            "parent_id": company.parent_id.id,
                            "username":users.login,
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
        
    @http.route("/trading/api/add_student", type="http",auth='public',cors="*", methods=["POST"], csrf=False)
    def add_student(self, **kw):
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

            registration_no = kw.get('registration_no')
            student_id = kw.get('student_id')
            username = kw.get('username')
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
                            "message": "School/Company not found"
                        }}),
                    content_type='application/json'
                )

            name = kw.get('name')
            name_np = kw.get('name_np')
            email = kw.get('email')
            mobile = kw.get('mobile')
            password = kw.get('password')
            profile_pic = kw.get('profile_pic')
            if profile_pic:
                if profile_pic == 'null':
                    profile_pic_binary = None
                else:
                    profile_pic_binary = base64.b64encode(profile_pic.read())
            else:
                profile_pic_binary = None

            users = request.env['res.users'].sudo().create({
                'name':name,
                'name_np':name_np,
                'login': username,
                'email': email,
                'mobile': mobile,
                'company_id': company.id,
                'company_ids': [(4, company.id)],
                'image_1920':profile_pic_binary,
            })
               
            if not users:
                return http.Response(
                    status=400,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": f"Student creation fail"
                        }}),
                    content_type='application/json'
                )
          
            users.sudo().write({'password': password})
            return http.Response(
                    status=200,
                    response=json.dumps({
                        "status":"success",
                        "data":{
                            "message": f"Student '{users.name}' created successfuly for School {company.name}"
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