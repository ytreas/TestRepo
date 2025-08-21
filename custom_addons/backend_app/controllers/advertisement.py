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

            # Cap check
            if user.ads_watched >= 10:
                return request.make_response(json.dumps({
                    'status': 'fail',
                    'message': 'Ad view limit reached. Try again tomorrow.',
                    'ads_watched_today': user.ads_watched,
                    'ads_cap': 10
                }), headers=[('Content-Type', 'application/json')], status=429)

            # Search for eligible ads (views > 0 and not already watched)
            domain = [
                ('status', '=', 'active'),
                ('views', '>', 0),
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

            # Pick a random ad
            ad = random.choice(ads)

            # Deduct 1 view from ad
            ad.sudo().write({'views': ad.views - 1})

            # Update counters and watched list
            watched_ids.append(ad.id)
            user.sudo().write({
                'ads_watched': user.ads_watched + 1,
                'watched_ad_ids_json': json.dumps(watched_ids)
            })

            image_url = (
                f"http://192.168.1.76:8069/web/image/advertisement.ad/{ad.id}/image"
                if ad.ad_type == 'image' else None
            )

            ad_data = {
                'id': ad.id,
                'name': ad.name,
                'ad_type': ad.ad_type,
                'status': ad.status,
                'duration': ad.duration,
                'reward': ad.reward,
                'target_url': ad.target_url,
                'video_url': ad.video_url,
                'views_remaining': ad.views,  # new: remaining views
                'image_url': image_url,
                'advertiser': ad.advertiser_id.name if ad.advertiser_id else None
            }

            return request.make_response(json.dumps({
                'status': 'success',
                'data': ad_data,
                'ads_watched_today': user.ads_watched + 1,  # after increment
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
            # Authenticate user
            auth_status, fail_resp = self.authenticate()
            if fail_resp:
                return fail_resp
            user_id = auth_status['user_id']
            user = request.env['res.users'].sudo().browse(user_id)
            # Extract request params
            name = request.params.get('name')
            views = request.params.get('views', 0)
            ad_type = request.params.get('ad_type')
            status = request.params.get('status', 'draft')
            duration = request.params.get('duration')
            reward = request.params.get('reward')
            cost = request.params.get('cost')
            target_url = request.params.get('target_url')
            video_url = request.params.get('video_url')

            # Handle optional image
            image_file = request.httprequest.files.get('image')
            image_data = None
            if image_file:
                image_data = base64.b64encode(image_file.read())

            # Convert numbers properly
            duration = int(duration) if duration else 0
            reward = int(reward) if reward else 0
            cost = int(cost) if cost else 0

            # Create advertisement
            ad = request.env['advertisement.ad'].sudo().create({
                'name': name,
                'ad_type': ad_type,
                'status': status,
                'duration': duration,
                'reward': reward,
                'cost': cost,
                'views': views,
                'target_url': target_url,
                'video_url': video_url,
                'advertiser_id': user.partner_id.id,  # link to partner
                'image': image_data,
            })
            if ad:
                # Deduct gems if user is NOT admin
                if not user.has_group('base.group_system'):  # Superuser/Admin group
                    if user.gems < cost:
                        return request.make_response(
                            json.dumps({'status': 'fail', 'message': 'Not enough gems to post ad'}),
                            headers=[('Content-Type', 'application/json')],
                            status=400
                        )
                    # Deduct gems
                    user.sudo().write({'gems': user.gems - cost})
                    request.env['gem.logs'].sudo().create({
                        'user_id': user.id,
                        'change_type': 'ad_post',
                        'gems_changed': -cost,
                        'date': fields.Datetime.now(),
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
            auth_status, fail_resp, user = self.authenticate(return_user=True)
            if fail_resp:
                return fail_resp

            data = json.loads(request.httprequest.data)
            ad = request.env['advertisement.ad'].sudo().browse(ad_id)

            if not ad.exists():
                return request.make_response(
                    json.dumps({'status': 'fail', 'message': 'Ad not found'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )

            # Only allow advertiser or admin to update
            if ad.advertiser_id != user.partner_id and not user.has_group('base.group_system'):
                return request.make_response(
                    json.dumps({'status': 'fail', 'message': 'Unauthorized to update this ad'}),
                    headers=[('Content-Type', 'application/json')],
                    status=403
                )

            ad.write({
                'name': data.get('name', ad.name),
                'ad_type': data.get('ad_type', ad.ad_type),
                'status': data.get('status', ad.status),
                'duration': data.get('duration', ad.duration),
                'reward': data.get('reward', ad.reward),
                'cost': data.get('cost', ad.cost),
                'target_url': data.get('target_url', ad.target_url),
                'video_url': data.get('video_url', ad.video_url),
                'views': data.get('views', ad.views),  # NEW: update views instead of dates
                'advertiser_id': data.get('advertiser_id', ad.advertiser_id.id),
            })

            return request.make_response(
                json.dumps({'status': 'success', 'message': 'Ad updated'}),
                headers=[('Content-Type', 'application/json')],
                status=200
            )

        except Exception as e:
            return http.Response(
                json.dumps({'status': 'fail', 'message': str(e)}),
                content_type="application/json",
                status=500
            )

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
