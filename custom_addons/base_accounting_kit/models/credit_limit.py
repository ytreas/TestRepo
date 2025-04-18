
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ResPartner(models.Model):
    """The Class inherits the res.partner model for adding the new
    fields and functions"""
    _inherit = 'res.partner'

    warning_stage = fields.Float(string='Warning Amount',
                                 help="A warning message will appear once the "
                                      "selected customer is crossed warning "
                                      "amount. Set its value to 0.00 to"
                                      " disable this feature")
    blocking_stage = fields.Float(string='Blocking Amount',
                                  help="Cannot make sales once the selected "
                                       "customer is crossed blocking amount."
                                       "Set its value to 0.00 to disable "
                                       "this feature")
    due_amount = fields.Float(string="Total Sale",
                              compute="compute_due_amount")
    active_limit = fields.Boolean("Active Credit Limit", default=False)

    enable_credit_limit = fields.Boolean(string="Credit Limit Enabled",
                                         compute="_compute_enable_credit_limit")

    def compute_due_amount(self):
        """Compute function to compute the due amount with the
         credit and debit amount"""
        for rec in self:
            if not rec.id:
                continue
            rec.due_amount = rec.credit - rec.debit

    def _compute_enable_credit_limit(self):
        """ Check credit limit is enabled in account settings """
        params = self.env['ir.config_parameter'].sudo()
        customer_credit_limit = params.get_param('customer_credit_limit',
                                                 default=False)
        for rec in self:
            rec.enable_credit_limit = True if customer_credit_limit else False

    @api.constrains('warning_stage', 'blocking_stage')
    def constrains_warning_stage(self):
        """Constrains functionality used to indicate or raise an
        UserError"""
        if self.active_limit and self.enable_credit_limit:
            if self.warning_stage >= self.blocking_stage:
                if self.blocking_stage > 0:
                    raise UserError(_(
                        "Warning amount should be less than Blocking amount"))


class SaleOrder(models.Model):
    """The Class inherits the sale.order model for adding the new
        fields and functions"""
    _inherit = 'sale.order'

    has_due = fields.Boolean(string='Has due')
    is_warning = fields.Boolean(string='Is warning')
    due_amount = fields.Float(string='Due Amount',
                              related='partner_id.due_amount')

    def _action_confirm(self):
        """To check the selected customers due amount is exceed than
        blocking stage"""
        if self.partner_id.active_limit \
                and self.partner_id.enable_credit_limit:
            if self.due_amount >= self.partner_id.blocking_stage:
                if self.partner_id.blocking_stage != 0:
                    raise UserError(_(
                        "%s is in  Blocking Stage and "
                        "has a due amount of %s %s to pay") % (
                                        self.partner_id.name, self.due_amount,
                                        self.currency_id.symbol))
        return super(SaleOrder, self)._action_confirm()

    @api.onchange('partner_id')
    def check_due(self):
        """To show the due amount and warning stage"""
        if self.partner_id and self.partner_id.due_amount > 0 \
                and self.partner_id.active_limit \
                and self.partner_id.enable_credit_limit:
            self.has_due = True
        else:
            self.has_due = False
        if self.partner_id and self.partner_id.active_limit\
                and self.partner_id.enable_credit_limit:
            if self.due_amount >= self.partner_id.warning_stage:
                if self.partner_id.warning_stage != 0:
                    self.is_warning = True
        else:
            self.is_warning = False


class AccountMove(models.Model):
    """The Class inherits the account.move model for adding the new
            fields and functions"""
    _inherit = 'account.move'

    has_due = fields.Boolean(string='Has due')
    is_warning = fields.Boolean(string='Is warning')
    due_amount = fields.Float(string="Due Amount",
                              related='partner_id.due_amount')

    def action_post(self):
        """To check the selected customers due amount is exceed than
        blocking stage"""
        pay_type = ['out_invoice', 'out_refund', 'out_receipt']
        for rec in self:
            if rec.partner_id.active_limit and rec.move_type in pay_type \
                    and rec.partner_id.enable_credit_limit:
                if rec.due_amount >= rec.partner_id.blocking_stage:
                    if rec.partner_id.blocking_stage != 0:
                        raise UserError(_(
                            "%s is in  Blocking Stage and "
                            "has a due amount of %s %s to pay") % (
                                            rec.partner_id.name, rec.due_amount,
                                            rec.currency_id.symbol))
        return super(AccountMove, self).action_post()

    @api.onchange('partner_id')
    def check_due(self):
        """To show the due amount and warning stage"""
        if self.partner_id and self.partner_id.due_amount > 0 \
                and self.partner_id.active_limit \
                and self.partner_id.enable_credit_limit:
            self.has_due = True
        else:
            self.has_due = False
        if self.partner_id and self.partner_id.active_limit \
                and self.partner_id.enable_credit_limit:
            if self.due_amount >= self.partner_id.warning_stage:
                if self.partner_id.warning_stage != 0:
                    self.is_warning = True
        else:
            self.is_warning = False
