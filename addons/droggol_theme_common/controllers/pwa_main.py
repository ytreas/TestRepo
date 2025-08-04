# -*- coding: utf-8 -*-
# Copyright (c) 2019-Present Droggol. (<https://www.droggol.com/>)

import hashlib
import json
import base64
import io
import string
from functools import partial

from odoo import http
from odoo.http import request

from odoo.modules.module import get_resource_path
from odoo.tools.mimetypes import guess_mimetype


class DroggolThemePWACommon(http.Controller):

    @http.route(['/droggol_theme_common/<int:website_id>/manifest.json'], type='http', auth='public', website=True)
    def get_pwa_manifest(self, website_id, **kargs):
        website = request.website
        manifest_data = {"fake": 1}
        if website and website.id == website_id and website.has_pwa:
            manifest_data = {
                "name": website.pwa_name,
                "short_name": website.pwa_short_name,
                "display": "standalone",
                "background_color": website.pwa_background_color,
                "theme_color": website.pwa_theme_color,
                "start_url": website.pwa_start_url,
                "scope": "/",
                "icons": [{
                    "src": "/web/image/website/%s/pwa_icon_192/192x192" % website.id,
                    "sizes": "192x192",
                    "type": "image/png",
                }, {
                    "src": "/web/image/website/%s/pwa_icon_512/512x512" % website.id,
                    "sizes": "512x512",
                    "type": "image/png",
                }]
            }
        return request.make_response(
            data=json.dumps(manifest_data),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route(['/service_worker.js'], type='http', auth='public', website=True, sitemap=False)
    def get_pwa_service_worker(self, **kargs):
        website = request.website
        js_folder = partial(get_resource_path, 'droggol_theme_common', 'static', 'src', 'js')
        file_path = js_folder('service_worker.js')
        data = open(file_path).read()
        offline_bool = 'true' if website.pwa_offline_page else 'false'
        data = data.replace('"##1##"', str(website.pwa_version))
        data = data.replace('"##2##"', offline_bool)

        return request.make_response(
            data=data,
            headers=[('Content-Type', 'text/javascript')]
        )

    @http.route(['/droggol_offline_page'], type='http', auth='public', website=True, cors="*", sitemap=False)
    def get_pwa_offline_page(self, **kargs):
        return request.render('droggol_theme_common.drg_pwa_offline_page', {})

    @http.route([
        '/pwa/logo.png',
    ], type='http', auth='public', website=True, cors="*", sitemap=False)
    def pwa_website_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        placeholder = partial(get_resource_path, 'web', 'static', 'src', 'img')
        website = request.website

        if not website.logo:
            response = http.send_file(placeholder('nologo.png'))
        else:
            b64 = website.logo
            image_base64 = base64.b64decode(b64)
            image_data = io.BytesIO(image_base64)
            mimetype = guess_mimetype(image_base64, default='image/png')
            imgext = '.' + mimetype.split('/')[1]
            if imgext == '.svg+xml':
                imgext = '.svg'
            response = http.send_file(image_data, filename=imgname + imgext, mimetype=mimetype, mtime=website.write_date)
        return response

    @http.route(['/pwa/is_pwa_active'], type='http', auth='public', website=True, sitemap=False)
    def get_pwa_is_active(self, **kargs):
        website = request.website
        data = {'pwa': website.has_pwa}
        return request.make_response(
            data=json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )
