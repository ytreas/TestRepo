from odoo import models, fields, api

class Advertisement(models.Model):
    _name = 'advertisement.ad'
    _description = 'Advertisement'
    _rec_name = 'name'

    name = fields.Char(string='Ad Name', required=True)
    
    ad_type = fields.Selection([
        ('image', 'Image'),
        ('video', 'Video'),
        ('url', 'URL'),
        # ('popup', 'Popup'),
        # ('text', 'Text'),
    ], string='Ad Type', required=True, default='image')
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('expired', 'Expired')
    ], string='Status', default='draft', required=True)

    duration = fields.Integer(string='Duration (seconds)', help="For video or popup ads")
    reward = fields.Integer(string='Reward', required=True)

    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')

    target_url = fields.Char(string='Target URL', help='URL where the ad redirects users')
    
    image = fields.Binary(string='Ad Image', attachment=False)
    video_url = fields.Char(string='Video URL', help='YouTube or CDN link for video ads')

    impressions = fields.Integer(string='Impressions', default=0, readonly=True)
    clicks = fields.Integer(string='Clicks', default=0, readonly=True)

    advertiser_id = fields.Many2one('res.partner', string='Advertiser', help='Linked to customer/company who owns the ad')

    # active = fields.Boolean(default=True)

    @api.depends('start_date', 'end_date')
    def _compute_status(self):
        for ad in self:
            if ad.end_date and fields.Datetime.now() > ad.end_date:
                ad.status = 'expired'

    # @api.onchange('ad_type')
    # def _onchange_ad_type(self):
    #     if self.ad_type != 'video':
    #         self.video_url = False
    #     if self.ad_type != 'image':
    #         self.image = False
