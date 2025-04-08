import pytz
from datetime import datetime, timezone
from odoo.http import request


class NepalTZ:
    @staticmethod
    def get_nepal_time():
        utc_time = datetime.now(timezone.utc)

        nepal_tz = pytz.timezone("Asia/Kathmandu")
        nepal_time = utc_time.astimezone(nepal_tz)
        print("dat time", nepal_time.strftime("%Y-%m-%d %H:%M"))

        return nepal_time.strftime("%Y-%m-%d %H:%M")


class EcomUtils:

    @staticmethod
    def get_current_origin():
        """
            Returns current request details
        """
        return {
            "url": request.httprequest.url,
            "origin_url":request.httprequest.host_url,
            "method": request.httprequest.method,
            "headers": dict(request.httprequest.headers),
            "query_string": request.httprequest.query_string.decode(),
            "params": request.params,
            "cookies": request.httprequest.cookies,
            "remote_addr": request.httprequest.remote_addr,
            "user_agent": request.httprequest.user_agent.string,
        }
