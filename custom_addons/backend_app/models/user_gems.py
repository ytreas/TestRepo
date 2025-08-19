from odoo import models, fields
from odoo import models, fields, api, exceptions
from datetime import datetime, date
import json

class ResUsers(models.Model):
    _inherit = 'res.users'

    gems = fields.Integer(string='Gems', default=0)
    gems_streak = fields.Integer(string="Gems Streak", default=0)
    last_gem_claim_date = fields.Datetime(string="Last Gem Claimed At")
    claimed_days_json = fields.Text(string="Claimed Days This Week", default='{}')
    ads_watched = fields.Integer(string="Ads Watched", default=0)
    last_ads_watch_reset = fields.Date(string="Last Ads Watched Reset")
    watched_ad_ids_json = fields.Text(string="Watched Ad IDs", default='[]')
    register_otp = fields.Char(string="OTP", help="One Time Password for verification", default='')
    register_otp_expiry = fields.Datetime(string="OTP Expiry", help="Expiry time for the OTP")
    reset_password_otp = fields.Char(string="Reset Password OTP", help="OTP for resetting password", default='')
    reset_password_otp_expiry = fields.Datetime(string="Reset Password OTP Expiry", help="Expiry time for the Reset Password OTP")
    is_register_validated = fields.Boolean(string="Is Validated", default=False)
    
    @api.model
    def create(self, vals):
        # Validate before creation
        self._validate_user_data(vals)
        return super(ResUsers, self).create(vals)

    def write(self, vals):
        # Validate before writing
        self._validate_user_data(vals)
        return super(ResUsers, self).write(vals)

    def _validate_user_data(self, vals):
        """Centralized validation method with gem abuse prevention"""
        # Basic value validations
        if 'gems' in vals:
            if vals['gems'] < 0:
                raise exceptions.ValidationError("Gems count cannot be negative")
            if vals['gems'] > 1000000:  # Reasonable upper limit
                raise exceptions.ValidationError("Abnormally high gem count detected")
        
        if 'gems_streak' in vals:
            if vals['gems_streak'] < 0:
                raise exceptions.ValidationError("Gems streak cannot be negative")
            if vals['gems_streak'] > 365:  # Max 1 year streak
                raise exceptions.ValidationError("Impossibly long streak detected")
        
        if 'ads_watched' in vals and vals['ads_watched'] < 0:
            raise exceptions.ValidationError("Ads watched count cannot be negative")
        
        # JSON format validations
        if 'claimed_days_json' in vals:
            try:
                claimed_days = json.loads(vals.get('claimed_days_json', '{}'))
                if not isinstance(claimed_days, dict):
                    raise ValueError
                # Validate max 7 days per week
                if len(claimed_days) > 7:
                    raise exceptions.ValidationError("Cannot claim more than 7 days per week")
            except ValueError:
                raise exceptions.ValidationError("Invalid JSON format for claimed days")
        
        if 'watched_ad_ids_json' in vals:
            try:
                ad_ids = json.loads(vals.get('watched_ad_ids_json', '[]'))
                if not isinstance(ad_ids, list):
                    raise ValueError
                # Prevent duplicate ads
                if len(ad_ids) != len(set(ad_ids)):
                    raise exceptions.ValidationError("Duplicate ad IDs detected")
                # Reasonable daily ad limit
                if len(ad_ids) > 50:
                    raise exceptions.ValidationError("Excessive ad watches detected")
            except ValueError:
                raise exceptions.ValidationError("Invalid JSON format for watched ad IDs")
        
        # Advanced gem validation logic
        # if 'gems' in vals or 'gems_streak' in vals:
        #     current_gems = self.gems if 'gems' not in vals else vals['gems']
        #     current_streak = self.gems_streak if 'gems_streak' not in vals else vals['gems_streak']
            
        #     # Validate gem/streak ratio (e.g., max 10 gems per streak day)
        #     # if current_streak > 0 and current_gems > current_streak * 10:
        #     #     raise exceptions.ValidationError("Gem count disproportionately high for streak length")
            
        #     # If updating both, validate the increment is reasonable
        #     if 'gems' in vals and 'gems_streak' in vals:
        #         gem_increment = vals['gems'] - self.gems
        #         streak_increment = vals['gems_streak'] - self.gems_streak
                
        #         # Prevent large gem jumps without streak increase
        #         if gem_increment > 100 and streak_increment <= 0:
        #             raise exceptions.ValidationError("Suspicious gem accumulation without streak progress")
        
        # Time-based validations if dates are being updated
        # if 'last_gem_claim_date' in vals:
        #     claim_date = fields.Datetime.from_string(vals['last_gem_claim_date'])
        #     if claim_date > fields.Datetime.now():
        #         raise exceptions.ValidationError("Future claim dates are not allowed")
        
        # if 'last_ads_watch_reset' in vals:
        #     reset_date = fields.Date.from_string(vals['last_ads_watch_reset'])
        #     if reset_date > fields.Date.today():
        #         raise exceptions.ValidationError("Future reset dates are not allowed")
    
class GemLogs(models.Model):
    _name = 'gem.logs'
    _description = 'Gem Logs'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    change_type = fields.Selection([
        ('claim', 'Claimed'),
        ('spend', 'Spent'),
        ('reward', 'Rewarded'),
        ('ad_watch', 'Ad Watch'),
        ('spin_win', 'Spin and Win'),
        ('admin', 'Admin Adjusted'),
        ('withdraw', 'Withdrawn'),
        ('connect_dot', 'Connect the Dots'),
        ('withdraw_rejected', 'Withdraw Rejected'),
    ], string='Type', required=True)
    gems_changed = fields.Integer(string='Gems Changed', required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)

class GemPayment(models.Model):
    _name = 'gem.payment'
    _description = 'Gem Payment Transactions'
    _order = 'create_date desc'
    
    STATUS_SELECTION = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]
    
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    gems = fields.Integer(string='Gems Purchased', required=True)
    amount = fields.Float(string='Amount', digits=(12, 2), required=True)
    phone = fields.Char(string='Phone Number', required=True)
    status = fields.Selection(STATUS_SELECTION, string='Status', default='draft')
    payment_date = fields.Datetime(string='Payment Date', default=fields.Datetime.now)
    payment_provider = fields.Char(string='Payment Provider', help='e.g., Esewa, Khalti, etc.')