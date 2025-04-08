from odoo import http,_
from odoo.http import Response,request
from werkzeug.exceptions import BadRequest,NotFound
import json
class ProductRecommendations(http.Controller):
    
    
    @http.route("/create_user_activity",type='json',auth='public',cors='*')
    def create_user_activity(self,**kwargs):
        user_id = kwargs.get('user_id')
        product_id = kwargs.get('product_id')
        session_id = kwargs.get('session_id')
        search_query = kwargs.get('search_query')
        activity_type = kwargs.get('activity_type', 'view')
        country_name=request.geoip.country_name
        country_code=request.geoip.country_code
        ip=request.geoip.ip
        request.env['user.activity.log'].sudo().create({
            'user_id': user_id,
            'session_id': session_id if not user_id else None,
            'product_id': product_id,
            'activity_type': activity_type,
            'search_query': search_query,
            'country_name':country_name,
            'country_code':country_code,
            'request_ip':ip,
        })
        return{
            'success':True
        }
        
        
    @http.route("/create_user_purchase_activity",type='json',auth='public',cors='*')
    def create_user_purchase_activity(self):
        
        request_data = request.httprequest.data
        data = json.loads(request_data)
        
        user_id = data.get('user_id')
        product_id = data.get('product_id')
        session_id = data.get('session_id')
        search_query = data.get('search_query')
        activity_type = data.get('activity_type', 'purchase')
        country_name=request.geoip.country_name
        country_code=request.geoip.country_code
        ip=request.geoip.ip
        request.env['user.activity.log'].sudo().create({
            'user_id': user_id,
            'session_id': session_id if not user_id else None,
            'product_id': product_id,
            'activity_type': activity_type,
            'search_query': search_query,
            'country_name':country_name,
            'country_code':country_code,
            'request_ip':ip,
        })
        return{
            'success':True
        }
        