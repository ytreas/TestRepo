from odoo.http import Response, request
from odoo import fields, http, api, SUPERUSER_ID
import logging
import json
from odoo.exceptions import ValidationError
import jwt
from . import jwt_token_auth

_logger = logging.getLogger(__name__)

class Intercompany(http.Controller):
    @http.route('/trading/api/get_intercompany', type='http',auth='public',cors="*", methods=['GET'], csrf=False)
    def get_intercompany(self, **kwargs):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            state = kwargs.get('state')
            source_company = kwargs.get('src_id')
            destination_company = kwargs.get('dst_id')
            sales_team = kwargs.get('sales_id')

            domain = []

            if state:
                domain.append(('state', '=', state))
            if source_company:
                domain.append(('src_company_id.id', '=', source_company))
            if destination_company:
                domain.append(('dst_company_id.id', '=', destination_company))
            if sales_team:
                domain.append(('crm_team_id.id', '=', sales_team))

            intercompany_transactions = request.env['inter.company.transfer.ept'].sudo().search(domain)

            intercompany_transactions_details = []

            for intercompany_transaction in intercompany_transactions:
                intercompany_transactions_details.append({
                    'id': intercompany_transaction.id,
                    'src_id': intercompany_transaction.src_company_id.id,
                    'src_name': intercompany_transaction.src_company_id.name_np if intercompany_transaction.src_company_id.name_np else intercompany_transaction.src_company_id.name,
                    'dst_id': intercompany_transaction.dst_company_id.id,
                    'dst_name': intercompany_transaction.dst_company_id.name_np if intercompany_transaction.dst_company_id.name_np else intercompany_transaction.dst_company_id.name,
                    'autoworkflow': intercompany_transaction.auto_workflow_id.name,
                    'sales_team': intercompany_transaction.crm_team_id.name if intercompany_transaction.crm_team_id.name else None,
                    'state': intercompany_transaction.state,
                    # 'product_id' : intercompany_transactions.inter_company_transfer_line_ids.inter_company_transfer_id.product_id.name,
                })

            return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data':{
                                'message': intercompany_transactions_details
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status= 200
                )
            
        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': 'Internal server error'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )

    @http.route('/trading/api/create_intercompany', type='http',auth='public',cors="*", methods=['POST'], csrf=False)
    def create_intercompany(self, **kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            # Explicitly check and set allowed_company_ids
            if 'allowed_company_ids' not in request.env.context:
                allowed_company_ids = request.env.user.company_ids.ids  # Get the current user's allowed companies
                request.env.context = dict(request.env.context, allowed_company_ids=allowed_company_ids)
            else:
                allowed_company_ids = request.env.context['allowed_company_ids']

            print(f"Allowed Company IDs: {allowed_company_ids}")
            # allowed_company_ids = kw.get('allowed_company_ids')
           
            if not allowed_company_ids:
                _logger.debug("allowed_company_ids context is not set or empty.")
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': 'Context "allowed_company_ids" not set'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )

            raw_data = request.httprequest.data
            json_data = json.loads(raw_data)
            source_company_id = json_data.get('src_id')
            destination_company_id = json_data.get('dst_id')
            auto_workflow = json_data.get('autoworkflow_id')
            crm_team = json_data.get('sales_id')
            
            if not source_company_id:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': 'Source Company Required'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            auto_workflow_id = request.env['inter.company.transfer.config.ept'].sudo().search([('id', '=', auto_workflow)], limit=1)
            crm_team_id = request.env['crm.team'].sudo().search([('id', '=', crm_team)], limit=1)
            src = request.env['res.company'].search([('id', '=', source_company_id)], limit=1)
            if not src:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': f'Source company "{source_company_id}" not found'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            if not destination_company_id:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': 'Destination company is required'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            dst = request.env['res.company'].search([('id', '=', destination_company_id)], limit=1)
            if not dst:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': f'Destination company "{destination_company_id}" not found'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            # Log company ids and context for debugging
            # _logger.info(f"Source Company ID: {src.id}, Destination Company ID: {dst.id}")
            # _logger.info(f"Allowed Company IDs: {allowed_company_ids}")

            # if src.id not in allowed_company_ids or dst.id not in allowed_company_ids:
            #     return request.make_response(
            #         json.dumps({
            #             'status': 'fail',
            #             'data':{
            #                     'message': 'Access to the company is not allowed'
            #                    }
            #         }),
            #         headers=[('Content-Type', 'application/json')],
            #         status=400
            #     )
            intercompany_vals = {
                'src_company_id': src.id,
                'dst_company_id': dst.id,
                'auto_workflow_id': auto_workflow_id.id,
                'crm_team_id': crm_team_id.id,
                'transaction_date': json_data.get('transaction_date'),
                'inter_company_transfer_line_ids': []
            }

            order_lines = json_data.get('order_lines',[])
            if not order_lines:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': f'At least one order line is required'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            for line in order_lines:
                product_id = line.get('product_id')
                if not product_id:
                    return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': f'Product id is required for each order line'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
                
            product = request.env['product.product'].search([('id', '=', product_id)], limit=1)
            if not product:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': f'Product not found: {product_id}'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            line_vals = {
                'product_id': product.id,
                # 'name': line.get('description',product.name),
                'quantity': line.get('quantity'),
                'price': line.get('price_unit'),
            }
            intercompany_vals['inter_company_transfer_line_ids'].append((0,0,line_vals))
            _logger.info(f"Creating Intercompany order: {intercompany_vals}")

            intercompany_transaction = request.env['inter.company.transfer.ept'].sudo().create(intercompany_vals)

            return request.make_response(
                    json.dumps({
                        'success': 'Intercompany created',
                        'source Company' : src.name,
                        'destination Company' : dst.name,
                        'product' : product.name,
                        'intercompany_transaction_id': intercompany_transaction.id,
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=200
                )    
        
        except ValidationError as ve:
            _logger.error(f"Validation error: {ve}")
            return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': str(ve)
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': str(e)
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )
        
    @http.route('/trading/api/process_intercompany_transaction/<int:id>',type='http',auth='public',cors="*",csrf=False,methods=['POST'])
    def process_intercompany_transaction(self,id,**kw):
        try:
            auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
            if auth_status['status'] == 'fail':
                return request.make_response(
                    json.dumps(auth_status),
                    headers=[('Content-Type', 'application/json')],
                    status=status_code
                )
            transfer = request.env['inter.company.transfer.ept'].sudo().search([('id', '=', id)])

            if not transfer.exists():
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': f'Intercompany transfer with id {id} not found'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
            
            if transfer.state not in ['draft','cancel']:
                return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': f'Intercompany transfer is in {transfer.state} state and cannot be processed'
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )

            transfer.sudo().with_context(from_api=True,default_type='ict').process_ict()
            return request.make_response(
                    json.dumps({
                        'status': 'success',
                        'data':{
                                'message': transfer.id
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=200
                )
        except Exception as e:
            _logger.error(f"Unexpected error confirming intercompany transfer {id}: {e}")
            return request.make_response(
                    json.dumps({
                        'status': 'fail',
                        'data':{
                                'message': str(e)
                               }
                    }),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )