from odoo import http,fields
from odoo.http import request
from datetime import datetime
import json
from . import jwt_token_auth  # Adjust path if different
from datetime import datetime, timedelta, timezone, date
import random
import base64

class AdvertisementAPI(http.Controller):

    def authenticate(self):
        auth_status, status_code = jwt_token_auth.JWTAuth.authenticate_request(self, request)
        if auth_status['status'] == 'fail':
            return None, request.make_response(
                json.dumps(auth_status),
                headers=[('Content-Type', 'application/json')],
                status=status_code
            )
        return auth_status, None

    @http.route('/api/ads', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
    def get_ads(self, **kwargs):
        try:
            auth_status, fail_resp = self.authenticate()
            if fail_resp:
                return fail_resp

            user_id = auth_status['user_id']
            user = request.env['res.users'].sudo().browse(user_id)

            now_utc = datetime.now(timezone.utc)
            gmt_plus_545 = now_utc + timedelta(hours=5, minutes=45)
            today_nepal = gmt_plus_545.date()

            # Reset daily counters if date changed
            if user.last_ads_watch_reset != today_nepal:
                user.write({
                    'ads_watched': 0,
                    'last_ads_watch_reset': today_nepal,
                    'watched_ad_ids_json': json.dumps([])
                })

            # Load watched ad IDs from DB
            try:
                watched_ids = json.loads(user.watched_ad_ids_json or '[]')
            except json.JSONDecodeError:
                watched_ids = []

            if user.ads_watched >= 10:
                return request.make_response(json.dumps({
                    'status': 'fail',
                    'message': 'Ad view limit reached. Try again tomorrow.',
                    'ads_watched_today': user.ads_watched,
                    'ads_cap': 10
                }), headers=[('Content-Type', 'application/json')], status=429)

            # Search for eligible ads
            domain = [
                ('status', '=', 'active'),
                ('start_date', '<=', now_utc),
                '|', ('end_date', '>=', now_utc), ('end_date', '=', False),
                ('id', 'not in', watched_ids)
            ]
            ads = request.env['advertisement.ad'].sudo().search(domain)

            if not ads:
                return request.make_response(json.dumps({
                    'status': 'fail',
                    'message': 'No more ads available to view today.',
                    'ads_watched_today': user.ads_watched,
                    'ads_cap': 10
                }), headers=[('Content-Type', 'application/json')], status=404)

            ad = random.choice(ads)

            # Update counters and watched list
            # watched_ids.append(ad.id)
            # user.write({
            #     'ads_watched': user.ads_watched + 1,
            #     'watched_ad_ids_json': json.dumps(watched_ids)
            # })

            # ad.impressions += 1  # optional
            image_url = (
                f"http://147.93.154.233:8071/web/image/advertisement.ad/{ad.id}/image"
                if ad.ad_type == 'image' else None
            )

            ad_data = {
                'id': ad.id if ad.id else None,
                'name': ad.name if ad.name else None,
                'ad_type': ad.ad_type if ad.ad_type else None,
                'status': ad.status if ad.status else None,
                'duration': ad.duration if ad.duration else None,
                'reward': ad.reward if ad.reward else None,
                'start_date': ad.start_date.strftime('%Y-%m-%d %H:%M:%S') if ad.start_date else None,
                'end_date': ad.end_date.strftime('%Y-%m-%d %H:%M:%S') if ad.end_date else None,
                'target_url': ad.target_url if ad.target_url else None,
                'video_url': ad.video_url if ad.video_url else None,
                'impressions': ad.impressions if ad.impressions else None,
                'image_url': image_url,
                'clicks': ad.clicks if ad.clicks else None,
                'advertiser': ad.advertiser_id.name if ad.advertiser_id else None
            }


            return request.make_response(json.dumps({
                'status': 'success',
                'data': ad_data,
                # 'ads_watched_today': user.ads_watched,  # after increment
                'ads_cap': 10
            }), headers=[('Content-Type', 'application/json')], status=200)

        except Exception as e:
            return http.Response(json.dumps({
                'status': 'fail',
                'message': str(e)
            }), content_type="application/json", status=500)


    # POST create ad (with optional image upload)
    @http.route('/api/ads', type='http', auth='public', csrf=False, cors="*", methods=['POST'])
    def create_ad(self, **kwargs):
        try:
            auth_status, fail_resp = self.authenticate()
            if fail_resp:
                return fail_resp

            # Use form data (multipart/form-data)
            name = request.params.get('name')
            ad_type = request.params.get('ad_type')
            status = request.params.get('status', 'draft')
            duration = request.params.get('duration')
            reward = request.params.get('reward')
            start_date = request.params.get('start_date')
            end_date = request.params.get('end_date')
            target_url = request.params.get('target_url')
            video_url = request.params.get('video_url')
            advertiser_id = request.params.get('advertiser_id')

            # Handle optional image
            image_file = request.httprequest.files.get('image')
            image_data = None
            if image_file:
                image_data = base64.b64encode(image_file.read())
            print(f"Image data: {image_data}")  # Debugging line
            ad = request.env['advertisement.ad'].sudo().create({
                'name': name,
                'ad_type': ad_type,
                'status': status,
                'duration': duration,
                'reward': reward,
                'start_date': start_date,
                'end_date': end_date,
                'target_url': target_url,
                'video_url': video_url,
                'advertiser_id': advertiser_id,
                'image': image_data,
            })

            return request.make_response(json.dumps({'status': 'success', 'id': ad.id}),
                                        headers=[('Content-Type', 'application/json')],
                                        status=201)

        except Exception as e:
            return http.Response(json.dumps({'status': 'fail', 'message': str(e)}),
                                content_type="application/json", status=500)


    # PUT update ad
    @http.route('/api/ads/<int:ad_id>', type='http', auth='public', csrf=False, cors="*", methods=['PUT'])
    def update_ad(self, ad_id, **kwargs):
        try:
            auth_status, fail_resp = self.authenticate()
            if fail_resp:
                return fail_resp

            data = json.loads(request.httprequest.data)
            ad = request.env['advertisement.ad'].sudo().browse(ad_id)

            if not ad.exists():
                return request.make_response(json.dumps({'status': 'fail', 'message': 'Ad not found'}),
                                             headers=[('Content-Type', 'application/json')],
                                             status=404)

            ad.write({
                'name': data.get('name', ad.name),
                'ad_type': data.get('ad_type', ad.ad_type),
                'status': data.get('status', ad.status),
                'duration': data.get('duration', ad.duration),
                'reward': data.get('reward', ad.reward),
                'start_date': data.get('start_date', ad.start_date),
                'end_date': data.get('end_date', ad.end_date),
                'target_url': data.get('target_url', ad.target_url),
                'video_url': data.get('video_url', ad.video_url),
                'advertiser_id': data.get('advertiser_id', ad.advertiser_id.id),
            })

            return request.make_response(json.dumps({'status': 'success', 'message': 'Ad updated'}),
                                         headers=[('Content-Type', 'application/json')],
                                         status=200)

        except Exception as e:
            return http.Response(json.dumps({'status': 'fail', 'message': str(e)}),
                                 content_type="application/json", status=500)

    # DELETE ad
    @http.route('/api/ads/<int:ad_id>', type='http', auth='public', csrf=False, cors="*", methods=['DELETE'])
    def delete_ad(self, ad_id, **kwargs):
        try:
            auth_status, fail_resp = self.authenticate()
            if fail_resp:
                return fail_resp

            ad = request.env['advertisement.ad'].sudo().browse(ad_id)
            if not ad.exists():
                return request.make_response(json.dumps({'status': 'fail', 'message': 'Ad not found'}),
                                             headers=[('Content-Type', 'application/json')],
                                             status=404)

            ad.unlink()
            return request.make_response(json.dumps({'status': 'success', 'message': 'Ad deleted'}),
                                         headers=[('Content-Type', 'application/json')],
                                         status=200)

        except Exception as e:
            return http.Response(json.dumps({'status': 'fail', 'message': str(e)}),
                                 content_type="application/json", status=500)

    @http.route('/api/ad_status', type='http', auth='public', csrf=False, cors="*", methods=['GET'])
    def get_ad_status(self, **kwargs):
        try:
            auth_status, fail_resp = self.authenticate()
            if fail_resp:
                return fail_resp

            user_id = auth_status['user_id']
            user = request.env['res.users'].sudo().browse(user_id)

            now_utc = datetime.now(timezone.utc)
            gmt_plus_545 = now_utc + timedelta(hours=5, minutes=45)
            today_nepal = gmt_plus_545.date()

            # Reset if it's a new day
            if user.last_ads_watch_reset != today_nepal:
                user.write({
                    'ads_watched': 0,
                    'last_ads_watch_reset': today_nepal,
                    'watched_ad_ids_json': json.dumps([])
                })

            remaining_ads = max(0, 10 - user.ads_watched)

            return request.make_response(json.dumps({
                'status': 'success',
                'message': 'Ad status retrieved successfully.',
                'ads_watched_today': user.ads_watched,
                'ads_remaining_today': remaining_ads,
                'ads_cap': 10,
                'last_reset_date': str(user.last_ads_watch_reset),
                'current_date': str(today_nepal)
            }), headers=[('Content-Type', 'application/json')], status=200)

        except Exception as e:
            return http.Response(json.dumps({
                'status': 'fail',
                'message': str(e)
            }), content_type="application/json", status=500)

    @http.route('/api/close_ad', type='http', auth='public', csrf=False, cors='*', methods=['POST'])
    def close_ad(self, **kwargs):
        try:
            # Authenticate via JWT (your own method)
            auth_status, fail_resp = self.authenticate()
            if fail_resp:
                return fail_resp

            user_id = auth_status['user_id']
            user = request.env['res.users'].sudo().browse(user_id)

            # Read raw JSON data from request body
            raw_data = request.httprequest.data
            try:
                json_data = json.loads(raw_data)
            except Exception:
                return request.make_response(json.dumps({
                    'status': 'fail',
                    'message': 'Invalid JSON data.'
                }), headers=[('Content-Type', 'application/json')], status=400)

            ad_id = json_data.get('ad')
            if not ad_id:
                return request.make_response(json.dumps({
                    'status': 'fail',
                    'message': 'Ad ID is required.'
                }), headers=[('Content-Type', 'application/json')], status=400)

            ad = request.env['advertisement.ad'].sudo().browse(int(ad_id))
            if not ad or not ad.exists():
                return request.make_response(json.dumps({
                    'status': 'fail',
                    'message': 'Invalid ad ID.'
                }), headers=[('Content-Type', 'application/json')], status=404)

            # Nepal timezone adjustment
            now_utc = datetime.now(timezone.utc)
            today_nepal = (now_utc + timedelta(hours=5, minutes=45)).date()

            if user.last_ads_watch_reset != today_nepal:
                user.write({
                    'ads_watched': 0,
                    'last_ads_watch_reset': today_nepal,
                    'watched_ad_ids_json': json.dumps([])
                })

            watched_ids = json.loads(user.watched_ad_ids_json or '[]')
            if ad.id in watched_ids:
                return request.make_response(json.dumps({
                    'status': 'fail',
                    'message': 'Ad already closed by user.'
                }), headers=[('Content-Type', 'application/json')], status=409)

            if user.ads_watched >= 10:
                return request.make_response(json.dumps({
                    'status': 'fail',
                    'message': 'Daily ad watch limit reached.'
                }), headers=[('Content-Type', 'application/json')], status=403)

            # Update gems and ad watch data
            watched_ids.append(ad.id)
            user.ads_watched += 1
            user.gems += ad.reward

            user.write({
                'ads_watched': user.ads_watched,
                'watched_ad_ids_json': json.dumps(watched_ids),
                'gems': user.gems
            })

            # Log the gem reward
            request.env['gem.logs'].sudo().create({
                'user_id': user.id,
                'change_type': 'ad_watch',
                'gems_changed': ad.reward,
                'date': fields.Datetime.now(),
            })


            return request.make_response(json.dumps({
                'status': 'success',
                'message': f'Ad closed. User rewarded with {ad.reward} gems.',
                'new_gems_total': user.gems,
                'ads_watched_today': user.ads_watched,
                'ad_id': ad.id
            }), headers=[('Content-Type', 'application/json')], status=200)

        except Exception as e:
            return http.Response(json.dumps({
                'status': 'fail',
                'message': str(e)
            }), content_type="application/json", status=500)
