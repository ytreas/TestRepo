from odoo import models, fields, api
from odoo.exceptions import UserError
import re

class ResUsersInherit(models.Model):
    _inherit = 'res.users'
    
    mobile = fields.Char(string="Mobile Number")
    can_add_users = fields.Boolean(string='Can Add Users', default=False)
    is_added_later = fields.Boolean(string='Is Added Later', default=True)

    @api.model
    def create(self, vals):
        # Validate mobile number
        mobile = vals.get('mobile', '')
        if mobile:
            if len(mobile) != 10 or not mobile.isdigit():
                raise UserError("Mobile number must be exactly 10 digits.")
            if not (mobile.startswith('97') or mobile.startswith('98')):
                raise UserError("Mobile number must start with '97' or '98'.")

        # Validate email address
        email = vals.get('email', '')
        if email:
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                raise UserError("Please enter a valid email address.")
            
        login_email = vals.get('login', '')
        if login_email:
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, login_email):
                raise UserError("Please enter a valid email address for login.")

        # If email is not provided, assign the company's email
        if not vals.get('email'):
            company = self.env['res.company'].browse(vals.get('company_id'))
            if company and company.email:
                vals['email'] = company.email 

        # Create the user
        user = super(ResUsersInherit, self).create(vals)
        
        return user
