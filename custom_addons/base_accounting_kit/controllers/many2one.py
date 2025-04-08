from odoo.http import Response, request
from odoo import http,api,SUPERUSER_ID
import datetime
from . import jwt_token_auth
import jwt
from datetime import date
import base64
import logging
import json

_logger = logging.getLogger(__name__)

class many2OneModels(http.Controller):

    @http.route("/trading/api/get_company", type="http",cors='*',auth="public", methods=["GET"], csrf=False)
    def get_company(self):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            # hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
     
            records = request.env['res.company'].sudo().search([])
               
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "name": record.name,
                        'name_np': record.name_np if record.name_np else None,
                        # "company_id":record.
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )

    @http.route("/trading/api/get_product_attributes", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_product_attributes(self):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            print("hehehr")
            # hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")

            # Fetch all product attributes
            attributes  = request.env['product.attribute'].sudo().search([])
            data = []

            for attr in attributes:
                # Fetch the attribute values for this attribute
                attr_values = request.env['product.attribute.value'].sudo().search([('attribute_id', '=', attr.id)])
                values = []
                for value in attr_values:
                    values.append({
                        "id": value.id,
                        "name": value.name,
                    })
                data.append({
                    "id": attr.id,
                    "name": attr.name,
                    "values": values
                })
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            _logger.error(f"Error in get_product_attributes: {str(e)}")
            return http.Response(
                status=500,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }}),
                content_type='application/json'
            )
    @http.route("/trading/api/get_province", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_province(self):
        try:
            records = request.env['location.province'].sudo().search([])
               
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "name": record.name,
                        "name_np": record.name_np
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
    @http.route("/trading/api/get_district", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_district(self,**kwargs):
        print("================================================================")
        try:
            domain = []
            province = kwargs.get('province_id')
            if province:
                domain.append(('province_name.id', '=', province))
            records = request.env['location.district'].sudo().search(domain)
               
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "name": record.district_name,
                        "province": record.province_name.id,
                        "name_np" :record.district_name_np
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
    @http.route("/trading/api/get_palika", type="http", auth='public',cors="*",methods=["GET"], csrf=False)
    def get_palika(self,**kwargs):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            domain = []
            district = kwargs.get('district_id')
            if district:
                domain.append(('district_name.id', '=', district))
            records = request.env['location.palika'].sudo().search(domain)
               
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "district": record.district_name.id,
                        "name": record.palika_name,
                        "name_np" :record.palika_name_np
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )

    @http.route("/trading/api/get_tole", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_tole(self,**kwargs):
        try:
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            domain = []
            palika = kwargs.get('palika_id')
            if palika:
                domain.append(('palika_name.id', '=', palika))
            records = request.env['location.tole'].sudo().search(domain)
               
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "palika": record.palika_name.id,
                        "name": record.tole_name,
                        "name_np" :record.tole_name_np
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )   
    
    @http.route("/trading/api/get_journal", type="http", auth='public',cors="*",methods=["GET"], csrf=False)
    def get_journal(self,**kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            # hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            company_id = kwargs.get("company_id")
            domain = []

            print("Company id",company_id)
            if company_id:
                domain.append(('company_id.id', '=', company_id))

            records = request.env['account.journal'].sudo().search(domain)
               
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "name": record.name,
                        'name_np': record.name_np if record.name_np else None,
                        "type" :record.type,
                        # "company_id":record.company_id.id
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )   
    
    @http.route("/trading/api/get_payment_method", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_payment_method(self,**kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")
            journal_id = kwargs.get("journal_id")
            domain=[]
            if journal_id:
                domain.append(('journal_id.id', '=', journal_id))
            records = request.env['account.payment.method.line'].sudo().search(domain)
            payment_methods = list(set([record.payment_method_id for record in records]))
            print(records)   
            data = []
            for record in payment_methods:
                data.append(
                    {
                        "id": record.id,
                        "name": record.name,
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )  
            
    @http.route("/trading/api/get_advance_payment_method", auth='public',cors="*",type="http", methods=["GET"], csrf=False)
    def get_advance_payment_method(self):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            # hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")

            records = request.env['sale.advance.payment.inv'].sudo().search([])  
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "name": record.advance_payment_method,
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )  
    
    @http.route("/trading/api/get_auto_workflow", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_auto_workflow(self):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            # hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")

            records = request.env['inter.company.transfer.config.ept'].sudo().search([])  
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "name": record.name,
                        'name_np': record.name_np if record.name_np else None,
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )  
    
    @http.route("/trading/api/get_crm_team_id", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_crm_team_id(self):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            # hosturl = request.httprequest.environ.get("HTTP_REFERER", "n/a")

            records = request.env['crm.team'].sudo().search([])  
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "name": record.name,
                        'name_np': record.name_np if record.name_np else None,
                    }
                )
            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )  
        
    @http.route("/trading/api/get_product_category", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_product_category(self):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            records = request.env['product.template'].sudo().search([])
            data = []
            
            for record in records:
                data.append(
                    {
                        "id": record.categ_id.id,
                        "name": record.categ_id.name,
                    }
                )
                return request.make_response(
                    json.dumps({"status": "success", "data": data}),
                    headers=[("Content-Type", "application/json")]
                )
            
        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
        
    @http.route("/trading/api/get_bank", type="http",auth='public',cors="*", methods=["GET"], csrf=False)
    def get_bank(self):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            records = request.env['res.partner.bank'].sudo().search([])
            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "name": record.display_name if record.display_name else None,
                        "acc_holder_name": record.acc_holder_name if record.acc_holder_name else None,
                        "acc_number": record.acc_number if record.acc_number else None,
                        "bank_name": record.bank_name if record.bank_name else None,
                        "bank_id": record.bank_id.id if record.bank_id.id else None,
                        "company_id": record.company_id.id if record.company_id.id else None,
                    }
                )
                return request.make_response(
                    json.dumps({"status": "success", "data": data}),
                    headers=[("Content-Type", "application/json")]
                )
        
        except Exception as e:
            return http.Response(
                    status=401,
                    response=json.dumps({
                        "status":"fail",
                        "data":{
                            "message": str(e)
                        }}),
                    content_type='application/json'
                )
        
    @http.route("/trading/api/get_company_type", type="http", auth='public', cors="*", methods=["GET"], csrf=False)
    def get_company_type(self):
        try:  
            model = request.env['company.register']
            company_type_field = model.fields_get(['company_type'])['company_type']
            company_type_options = [option[1] for option in company_type_field['selection']]

            return request.make_response(
                json.dumps({"status": "success", "data": company_type_options}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                status=401,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }}),
                content_type='application/json'
            )
        
    @http.route("/trading/api/get_organization_type", type="http", auth='public', cors="*", methods=["GET"], csrf=False)
    def get_organization_type(self):
        try:
            model = request.env['company.register']
            organization_type_field = model.fields_get(['organization_type'])['organization_type']
            organization_type_options = [option[1] for option in organization_type_field['selection']]

            return request.make_response(
                json.dumps({"status": "success", "data": organization_type_options}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                status=401,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }}),
                content_type='application/json'
            )
        
    @http.route("/trading/api/get_gender", type="http", auth='public', cors="*", methods=["GET"], csrf=False)
    def get_gender(self):
        try:
            model = request.env['company.register']
            gender_field = model.fields_get(['gender'])['gender']
            gender_options = [option[1] for option in gender_field['selection']]

            return request.make_response(
                json.dumps({"status": "success", "data": gender_options}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return http.Response(
                status=401,
                response=json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }}),
                content_type='application/json'
            )

    @http.route("/trading/api/create_documents_type", type="json", auth="public", cors="*", methods=["POST"], csrf=False)
    def create_documents_type(self, **kwargs):
        try:
            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)
            name = json_data.get("name")
            code = json_data.get("code")

            if not name or not code:
                return request.make_response(
                    json.dumps({"status": "fail", "data": {"message": "Name and Code are required fields."}}),
                    headers=[("Content-Type", "application/json")],
                    status=400
                )

            new_record = request.env["documents.types"].sudo().create({"name": name, "code": code})

            return request.make_response(
                json.dumps({"status": "success", "data": {"id": new_record.id, "name": new_record.name, "code": new_record.code}}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": "fail", "data": {"message": str(e)}}),
                headers=[("Content-Type", "application/json")],
                status=500
            )

    @http.route("/trading/api/get_individual_field_selection", type="http", auth='public', cors="*", methods=["GET"], csrf=False)
    def get_individual_field_selection(self):
        try:
            records = request.env['individual.field.selection'].sudo().search([])
            data = [{
                "id": record.id,
                "name": record.name or None,
            } for record in records]

            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": "fail", "message": str(e)}),
                headers=[("Content-Type", "application/json")],
                status=500
            )

    @http.route("/trading/api/get_organization_field_selection", type="http", auth='public', cors="*", methods=["GET"], csrf=False)
    def get_organization_field_selection(self):
        try:
            records = request.env['organization.field.selection'].sudo().search([])
            data = [{
                "id": record.id,
                "name": record.name or None,
            } for record in records]

            return request.make_response(
                json.dumps({"status": "success", "data": data}),
                headers=[("Content-Type", "application/json")]
            )

        except Exception as e:
            return request.make_response(
                json.dumps({"status": "fail", "message": str(e)}),
                headers=[("Content-Type", "application/json")],
                status=500
            )

    @http.route("/trading/api/get_location", type="http", auth='public', cors="*", methods=["GET"], csrf=False)
    def get_location(self, **kwargs):
        try:
            # Authenticate the request
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            
            # Set up domain filters based on parameters
            print("Request Parameters",kwargs)
            domain = []
            location_id = kwargs.get('location_id')
            print("Location ID",location_id)
            company_id = kwargs.get('company_id')
            location_type = kwargs.get('location_type')
            usage = kwargs.get('usage')
            is_scrap = kwargs.get('is_scrap')
            
            # Apply filters
            if location_id:
                domain.append(('id', '=', int(location_id)))
            if company_id:
                domain.append(('company_id', '=', int(company_id)))
            if location_type:
                domain.append(('location_type', '=', location_type))
            if usage:
                domain.append(('usage', '=', usage))
            if is_scrap is not None:
                is_scrap_bool = is_scrap.lower() == 'true'
                domain.append(('scrap_location', '=', is_scrap_bool))
            print("Domain",domain)
            # Fetch locations based on domain
            locations = request.env['stock.location'].sudo().search(domain)
            
            # Prepare response data
            data = []
            for location in locations:
                location_data = {
                    "id": location.id,
                    "name": location.name if location.name else None,
                    "name_np": location.name_np if hasattr(location, 'name_np') and location.name_np else None,
                    "complete_name": location.complete_name if location.complete_name else None,
                    "usage": location.usage if location.usage else None,
                    "location_type": location.location_type if hasattr(location, 'location_type') and location.location_type else None,
                    "posx": location.posx if hasattr(location, 'posx') else None,
                    "posy": location.posy if hasattr(location, 'posy') else None,
                    "posz": location.posz if hasattr(location, 'posz') else None,
                    "barcode": location.barcode if location.barcode else None,
                    "parent_id": location.location_id.id if location.location_id else None,
                    "parent_name": location.location_id.name if location.location_id and location.location_id.name else None,
                    "company_id": location.company_id.id if location.company_id else None,
                    "company_name": location.company_id.name if location.company_id and location.company_id.name else None,
                    "is_scrap": location.scrap_location if hasattr(location, 'scrap_location') else False,
                    "return_location": location.return_location if hasattr(location, 'return_location') else False,
                    "removal_strategy_id": location.removal_strategy_id.id if hasattr(location, 'removal_strategy_id') and location.removal_strategy_id else None,
                    "removal_strategy_name": location.removal_strategy_id.name if hasattr(location, 'removal_strategy_id') and location.removal_strategy_id and location.removal_strategy_id.name else None
                }
                
                # Add child locations if they exist
                child_locations = request.env['stock.location'].sudo().search([('location_id', '=', location.id)])
                if child_locations:
                    location_data["child_locations"] = [{
                        "id": child.id,
                        "name": child.name,
                        "complete_name": child.complete_name if child.complete_name else None
                    } for child in child_locations]
                
                data.append(location_data)
            if location_id:
                    return request.make_response(
                    json.dumps({"status": "success", "data": data[0]}),
                    headers=[("Content-Type", "application/json")]
                )
            else:
                return request.make_response(
                    json.dumps({"status": "success", "data": data}),
                    headers=[("Content-Type", "application/json")]
                )

        except ValueError as e:
            return request.make_response(
                json.dumps({
                    "status": "fail",
                    "data": {
                        "message": f"Invalid parameter value: {str(e)}"
                    }
                }),
                headers=[("Content-Type", "application/json")],
                status=400
            )
        except Exception as e:
            _logger.exception(f"Error in get_location: {str(e)}")
            return request.make_response(
                json.dumps({
                    "status": "fail",
                    "data": {
                        "message": str(e)
                    }
                }),
                headers=[("Content-Type", "application/json")],
                status=500
            )