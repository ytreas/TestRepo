
from odoo import models, _,fields,api
from odoo.exceptions import RedirectWarning
from odoo.exceptions import ValidationError

class ResCompany(models.Model):
    _inherit = "res.company"

    company_detail_ids = fields.One2many("res.company.details","parent_id",string=_("Company Details"))
    login_bg_img = fields.Binary("Login Background Image",required=False)

    province = fields.Many2one('location.province',string=_('Province'),required=False)
    district = fields.Many2one('location.district',string=_('District'))
    palika = fields.Many2one('location.palika',string=_('Palika'),required=False)
    ward_no = fields.Integer(string=_('Ward No'),required=False)
    tole = fields.Many2one('location.tole',string=_('Tole'))
    full_address = fields.Char("Address",compute="_compute_full_address")
    show_tax = fields.Boolean("Show tax in invoice",default=True)
    # login_bg_img = fields.Binary("Login Background Image",required=False)
    street_np = fields.Char(string=_("Address NEP"), store = True)
    citizenship_detail_mandatority = fields.Boolean(string=_("Is Citizenship Details Mandatory"))

    company_code = fields.Char(string=_('Company Code'),required=False,size=15)
    fax_number = fields.Char(string=_('Fax Number'),required=False)
    pf_code = fields.Char(string='PF Code')
    cit_code = fields.Char(string='Cit Code')
    cit_name = fields.Char(string="CIT Name")
    cit_address = fields.Char(string="CIT Address")
    name_np = fields.Char(string=_('Company Nepali Name'),required=False, store = True)
    gender = fields.Selection([('male','male'),('female','female'),('others','others')],string="Gender")
    # name = fields.Char(string="Name(EN)", required=False, translate=True)
    # Currency field, setting default currency to NPR
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self._get_default_currency()
    )
    contact_person = fields.Many2one('res.partner',string="Contact Person")

    @api.model
    def _get_default_currency(self):
        """Returns the default currency for NPR (Nepalese Rupees)."""
        return self.env['res.currency'].search([('name', '=', 'NPR')], limit=1).id
    
    def _compute_full_address(self):
        for record in self:
            temp=""
            if record.palika:
                temp+=record.palika.palika_name
            if record.ward_no:
                temp+=' - '+str(record.ward_no)+', '
            if record.district:
                temp+=record.district.district_name+', '
            if record.province:
                temp+=record.province.name
            
            record.full_address = temp

    def _validate_fiscalyear_lock(self, values):
        if values.get('fiscalyear_lock_date'):
            draft_entries = self.env['account.move'].search([
                ('company_id', 'in', self.ids),
                ('state', '=', 'draft'),
                ('date', '<=', values['fiscalyear_lock_date'])])
            if draft_entries:
                error_msg = _('There are still unposted entries in the '
                              'period you want to lock. You should either post '
                              'or delete them.')
                action_error = {
                    'view_mode': 'tree',
                    'name': 'Unposted Entries',
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', draft_entries.ids)],
                    'search_view_id': [self.env.ref(
                        'account.view_account_move_filter').id, 'search'],
                    'views': [[self.env.ref(
                        'account.view_move_tree').id, 'list'],
                              [self.env.ref('account.view_move_form').id,
                               'form']],
                }
                raise RedirectWarning(error_msg, action_error,
                                      _('Show unposted entries'))
            unreconciled_statement_lines = self.env[
                'account.bank.statement.line'].search([
                ('company_id', 'in', self.ids),
                ('is_reconciled', '=', False),
                ('date', '<=', values['fiscalyear_lock_date']),
                ('move_id.state', 'in', ('draft', 'posted')),
            ])
            if unreconciled_statement_lines:
                error_msg = _(
                    "There are still unreconciled bank statement lines in the "
                    "period you want to lock."
                    "You should either reconcile or delete them.")
                action_error = {
                    'view_mode': 'tree',
                    'name': 'Unreconciled Transactions',
                    'res_model': 'account.bank.statement.line',
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', unreconciled_statement_lines.ids)],
                    'views': [[self.env.ref(
                        'base_accounting_kit.view_bank_statement_line_tree').id,
                               'list']]
                }
                raise RedirectWarning(error_msg, action_error,
                                      _('Show Unreconciled Bank'
                                        ' Statement Line'))
                
    def create(self, vals):
        print("before ids", vals.get('company_category'))
        
        if 'company_category' in vals:
            default_coa_category = self.env['company.category'].sudo().search([('code', '=', '1000000001')], limit=1)
            default_ids = [default_coa_category.id] if default_coa_category else []

            current_ids = vals['company_category'][0][2] if vals['company_category'] else []
        else:
            current_ids = []
        
        missing_ids = [id for id in default_ids if id not in current_ids]
        if missing_ids:
            current_ids.extend(missing_ids)
        
        vals['company_category'] = [(6, 0, current_ids)]
        print("current_ids", current_ids)

        return super(ResCompany, self).create(vals)

class ResCompanyDetails(models.Model):
    _name = 'res.company.details'
    _description = 'Company Details'

    parent_id = fields.Many2one("res.company",string=_("Company"))
    url = fields.Char("Web URL")

    @api.constrains('url')
    def _check_unique_url(self):
        for record in self:
            if record.url:
                existing_record = self.search([('url', '=', record.url), ('id', '!=', record.id)])
                if existing_record:
                    raise ValidationError('URL must be unique!')
                
                

    
    