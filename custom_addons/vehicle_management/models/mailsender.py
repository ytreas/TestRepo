from odoo import models, _
from odoo.exceptions import UserError

class MailSender:
    def __init__(self, env):
        self.env = env

    def send_mail(self, email_to, subject, body_html, model=None, res_id=None, raise_exception=True):
        """
        Generic method to send emails
        Args:
            email_to: recipient email address
            subject: email subject
            body_html: email body in HTML format
            model: model name (optional)
            res_id: record ID (optional)
            raise_exception: whether to raise exception if email fails (default: True)
        """
        # print(f"Sending email to: {email_to}")
        
        if not email_to:
            message = "Email address is not available for the recipient."
            # print(message)
            if raise_exception:
                raise UserError(_(message))
            return False

        try:
            mail_values = {
                'subject': subject,
                'body_html': body_html,
                'email_to': email_to,
            }
            
            if model:
                mail_values['model'] = model
            if res_id:
                mail_values['res_id'] = res_id

            # print("mail_values:", mail_values)
            mail = self.env['mail.mail'].create(mail_values)
            # print("mail:", mail)
            mail.send()
            # print(f"Email sent successfully to: {email_to}")
            return True

        except Exception as e:
            message = f"Error sending email: {e}"
            # print(message)
            if raise_exception:
                raise UserError(_(message))
            return False