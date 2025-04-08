from odoo import http,_
from odoo.http import request
import pytz
from datetime import datetime, timezone


class NepalTZ:
    @staticmethod
    def get_nepal_time():
        utc_time = datetime.now(timezone.utc)

        nepal_tz = pytz.timezone("Asia/Kathmandu")
        nepal_time = utc_time.astimezone(nepal_tz)

        return nepal_time.strftime("%Y-%m-%d %H:%M")


class SendMail(http.Controller):
    
    @staticmethod
    def send_email(mail_to, subject=_("Test Mail"), email_template=None):

        try:
            recipient_email = mail_to
            subject = subject
            body = email_template
            if not recipient_email:
                return "Email address is required."
            if not email_template:
                return "Email template is required."

            mail_values = {
                "subject": subject,
                "email_to": recipient_email,
                "body_html": body,
                "email_from": request.env.user.email or "noreply@lekhaplus.com",
            }
            
            mail = request.env["mail.mail"].sudo().create(mail_values)
            mail.sudo().send()

            return True

        except Exception as e:
            print("errororororor", e)
            return False