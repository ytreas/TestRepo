from odoo import models, fields, api

class CustomBluebookRenewalRequest(models.TransientModel):
    _name = 'custom.bluebook.renewal.request'
    _description = 'Custom Bluebook Renewal Request'

    company_id = fields.Many2one('res.company', string='Company Name', required=True, default=lambda self: self.env.company)
    vehicle_company_id = fields.Many2one('custom.vehicle.company', string='Vehicle Company', required=True)
    owner_id = fields.Many2one('custom.vehicle.owner', string='Vehicle Owner', required=True, domain="[('vehicle_company_id', '=', vehicle_company_id)]")
    vehicle_number = fields.Many2one('vehicle.number', string='Vehicle Number', required=True)
    expiry_date = fields.Date(string='Expiry Date', required=True)
    expiry_date_bs = fields.Char(string='Expiry Date (Nepali)')
    last_renewal_date = fields.Date(string='Renewal Date', required=True)
    last_renewal_date_bs = fields.Char(string='Renewal Date (Nepali)')

    vehicle_number_domain = fields.Char(compute="_compute_vehicle_number_domain", store=False)

    @api.depends('owner_id')
    def _compute_vehicle_number_domain(self):
        for record in self:
            if record.owner_id:
                vehicle_ids = record.owner_id.vehicle_number.ids
                record.vehicle_number_domain = [('id', 'in', vehicle_ids)]
            else:
                record.vehicle_number_domain = [('id', 'in', [])]

    def confirm_renewal(self):
        # Logic to confirm bluebook renewal
        bluebook = self.env['custom.vehicle.bluebook'].search([('vehicle_number', '=', self.vehicle_number.number)], limit=1)
        if bluebook:
            bluebook.write({
                'expiry_date': self.expiry_date,
                'last_renewal_date': self.last_renewal_date
            })
        return {'type': 'ir.actions.act_window_close'}


class CustomPollutionRenewalRequest(models.TransientModel):
    _name = 'custom.pollution.renewal.request'
    _description = 'Custom Pollution Renewal Request'

    company_id = fields.Many2one('res.company', string='Company Name', required=True, default=lambda self: self.env.company)
    vehicle_company_id = fields.Many2one('custom.vehicle.company', string='Vehicle Company', required=True)
    owner_id = fields.Many2one('custom.vehicle.owner', string='Vehicle Owner', required=True, domain="[('vehicle_company_id', '=', vehicle_company_id)]")
    vehicle_number = fields.Many2one('vehicle.number', string='Vehicle Number', required=True)
    expiry_date = fields.Date(string='Expiry Date', required=True)
    expiry_date_bs = fields.Char(string='Expiry Date (Nepali)')
    last_renewal_date = fields.Date(string='Renewal Date', required=True)
    last_renewal_date_bs = fields.Char(string='Renewal Date (Nepali)')

    vehicle_number_domain = fields.Char(compute="_compute_vehicle_number_domain", store=False)

    @api.depends('owner_id')
    def _compute_vehicle_number_domain(self):
        for record in self:
            if record.owner_id:
                vehicle_ids = record.owner_id.vehicle_number.ids
                record.vehicle_number_domain = [('id', 'in', vehicle_ids)]
            else:
                record.vehicle_number_domain = [('id', 'in', [])]

    def confirm_renewal(self):
        # Logic to confirm pollution renewal
        pollution = self.env['custom.vehicle.pollution'].search([('vehicle_number', '=', self.vehicle_number.number)], limit=1)
        if pollution:
            pollution.write({
                'expiry_date': self.expiry_date,
                'last_renewal_date': self.last_renewal_date
            })
        return {'type': 'ir.actions.act_window_close'}


class CustomInsuranceRenewalRequest(models.TransientModel):
    _name = 'custom.insurance.renewal.request'
    _description = 'Custom Insurance Renewal Request'

    company_id = fields.Many2one('res.company', string='Company Name', required=True, default=lambda self: self.env.company)
    vehicle_company_id = fields.Many2one('custom.vehicle.company', string='Vehicle Company', required=True)
    owner_id = fields.Many2one('custom.vehicle.owner', string='Vehicle Owner', required=True, domain="[('vehicle_company_id', '=', vehicle_company_id)]")
    vehicle_number = fields.Many2one('vehicle.number', string='Vehicle Number', required=True)
    expiry_date = fields.Date(string='Expiry Date', required=True)
    expiry_date_bs = fields.Char(string='Expiry Date (Nepali)') 
    last_renewal_date = fields.Date(string='Renewal Date', required=True)
    last_renewal_date_bs = fields.Char(string='Renewal Date (Nepali)')
    insurance_company = fields.Char(string='Insurance Company')
    insurance_policy_number = fields.Char(string='Insurance Policy Number')
    bill_arrived = fields.Boolean(string='Bill Arrived')

    vehicle_number_domain = fields.Char(compute="_compute_vehicle_number_domain", store=False)

    @api.depends('owner_id')
    def _compute_vehicle_number_domain(self):
        for record in self:
            if record.owner_id:
                vehicle_ids = record.owner_id.vehicle_number.ids
                record.vehicle_number_domain = [('id', 'in', vehicle_ids)]
            else:
                record.vehicle_number_domain = [('id', 'in', [])]

    def confirm_renewal(self): 
        # Logic to confirm insurance renewal
        insurance = self.env['custom.vehicle.insurance'].search([('vehicle_number', '=', self.vehicle_number.number)], limit=1)
        if insurance:
            insurance.write({
                'expiry_date': self.expiry_date,
                'last_renewal_date': self.last_renewal_date,
                'bill_arrived': self.bill_arrived,
                'insurance_company': self.insurance_company,
                'insurance_policy_number': self.insurance_policy_number
            })
        return {'type': 'ir.actions.act_window_close'}

class CustomPermitRenewalRequest(models.TransientModel):
    _name = 'custom.permit.renewal.request'
    _description = 'Custom Permit Renewal Request'

    company_id = fields.Many2one('res.company', string='Company Name', required=True, default=lambda self: self.env.company) 
    vehicle_company_id = fields.Many2one('custom.vehicle.company', string='Vehicle Company', required=True)
    owner_id = fields.Many2one('custom.vehicle.owner', string='Vehicle Owner', required=True, domain="[('vehicle_company_id', '=', vehicle_company_id)]")
    vehicle_number = fields.Many2one('vehicle.number', string='Vehicle Number', required=True)
    expiry_date = fields.Date(string='Expiry Date', required=True)
    expiry_date_bs = fields.Char(string='Expiry Date (Nepali)')
    last_renewal_date = fields.Date(string='Renewal Date', required=True)
    last_renewal_date_bs = fields.Char(string='Renewal Date (Nepali)')
 
    vehicle_number_domain = fields.Char(compute="_compute_vehicle_number_domain", store=False)

    @api.depends('owner_id')
    def _compute_vehicle_number_domain(self):
        for record in self: 
            if record.owner_id:
                vehicle_ids = record.owner_id.vehicle_number.ids 
                record.vehicle_number_domain = [('id', 'in', vehicle_ids)]
            else:
                record.vehicle_number_domain = [('id', 'in', [])]

    def confirm_renewal(self):
        # Logic to confirm permit renewal
        permit = self.env['custom.vehicle.permit'].search([('vehicle_number', '=', self.vehicle_number.number)], limit=1)
        if permit:
            permit.write({
                'expiry_date': self.expiry_date,
                'last_renewal_date': self.last_renewal_date
            })
        return {'type': 'ir.actions.act_window_close'}
