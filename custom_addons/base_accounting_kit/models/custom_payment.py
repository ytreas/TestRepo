from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import uuid
from odoo.http import request
import nepali_datetime


class CustomPaymentMethods(models.Model):
    _name = "custom.payment.gateways"
    _rec_name = "payment_method_name"

    payment_method_name = fields.Selection(
        [
            ("esewa", "Esewa"),
            ("khalti", "Khalti"),
            ("Cash", "Cash"),
            ("Cheque Deposit", "Cheque"),
            ("Bank Transfer", "Bank Transfer"),
            ("imepay", "Imepay"),
            ("cips", "ConnectIPS"),
        ],
        required=True,
        default="esewa",
    )
    code = fields.Char()
    merchant_api = fields.Char("Merchant API")
    merchant_api_key = fields.Char("Merchant API Key")
    other_details = fields.Char("Other Details")
    bank = fields.Many2one("lekhaplus.bank")
    bank_account = fields.Char("Bank Account")
    bank_account_holder_name = fields.Char("Bank Account Holder Name")
    company_id = fields.Integer(
        "Company ID",
        tracking=True,
        default=lambda self: self.env.user.company_id,
        readonly=True,
    )

    @api.model
    def create(self, vals):
        if "company_id" not in vals:
            vals["company_id"] = self.env.user.company_id.id
        return super(CustomPaymentMethods, self).create(vals)


class LekhaPlusBank(models.Model):
    _name = "lekhaplus.bank"
    _rec_name = "official_name"

    name = fields.Char("Bank Name", required=True)
    location = fields.Char("Bank Location")
    code = fields.Char("Bank Code")
    official_name = fields.Char(store=True, compute="get_official_name")

    @api.depends("code", "name", "location")
    def get_official_name(self):
        for rec in self:
            rec.official_name = (
                f"[{rec.code or ''}]-{rec.name or ''}-{rec.location or ''}"
            )


class InheritAccountMove(models.Model):
    _inherit = "account.move"
    

    def lekhaplus_payment_form_button_action(self):

        try:
            if len(self.ids) > 1:
                raise ValidationError(
                    f"{_('The number of bills selected cannot be more than one.')}"
                )

            else:
                if self.amount_residual > 0:
                    action = {
                        "name": _("Lekha+ Payment"),
                        "res_model": "lekhaplus.payment.master",
                        "views": [[False, "form"]],
                        "context": {
                            "active_model": "account.move.line",
                            "active_ids": self.ids,
                            "account_move_id": self.id,
                            "amount_total": self.amount_residual,
                            "tax_amount": self.amount_tax,
                            "inv_lines_ids": self.invoice_line_ids.ids,
                            "invoice_lines": [(6, 0, self.invoice_line_ids.ids)],
                        },
                        "view_id": self.env.ref(
                            "base_accounting_kit.lekhaplus_payment_master_view_form"
                        ).id,
                        "type": "ir.actions.act_window",
                        "target": "new",
                    }

                    return action
                else:
                    raise ValidationError(
                        f"{_('The total payable amount must be greater than 0. Your total payable amount is ')}{self.amount_residual}"
                    )

        except Exception as e:
            raise ValidationError(f"[{e}]")


class LekhaPaymentMaster(models.Model):
    _name = "lekhaplus.payment.master"
    _rec_name = "token"
    _description = "Payment Information"

    payment_method = fields.Many2one("custom.payment.gateways")
    payment_titles = fields.Char("Payment title")
    client_id = fields.Many2one(
        "res.partner",
        default=lambda self: self.env.user.partner_id.id,
    )
    amount = fields.Float("Amount", store=True)
    tax_amount = fields.Float("Tax amount", store=True)
    transaction_date = fields.Char("Transaction Date", store=True)
    transaction_id = fields.Char("Transaction ID", store=True)
    payment_status = fields.Boolean(default=False)
    invoice_id = fields.Char("Invoice ID", store=True)
    account_move_id = fields.Many2one(
        "account.move", string="Account Move ID", store=True
    )
    token = fields.Char("token")
    tax_revenue_receipt_no = fields.Char("tax_revenue_receipt_no")
    remarks = fields.Char("Remarks", store=True)
    company_id = fields.Integer(
        "Company ID",
        tracking=True,
        default=lambda self: self.env.user.company_id,
        readonly=True,
    )
    voucher = fields.Binary("Voucher")

    payment_success_from_provider = fields.Boolean(default=False)
    show_voucher=fields.Boolean(compute='_compute_voucher_show_or_not')
    
    @api.depends('payment_method')
    def _compute_voucher_show_or_not(self):
        for rec in self:
            print("method",rec.payment_method.payment_method_name)
            if not rec.payment_method:
                rec.show_voucher = False
            else:
                if rec.payment_method.payment_method_name in ['Bank Transfer', 'Cheque Deposit', 'Cash']:
                    rec.show_voucher = True
                else:
                    rec.show_voucher = False
    @api.model
    def create(self, vals):
        rec_exists = (
            self.env["lekhaplus.payment.master"]
            .sudo()
            .search(
                [
                    ("account_move_id", "=", vals["account_move_id"]),
                    ("company_id", "=", self.env.user.company_id.id),
                ]
            )
        )
        if rec_exists.exists():
            rec_exists.unlink()
        return super(LekhaPaymentMaster, self).create(vals)

    @api.onchange("payment_status")
    def set_system_failed_payment(self):
        for account_move in self:
            try:
                if (
                    not account_move.payment_status
                    and account_move.payment_success_from_provider
                ):
                    account_move_id = request.env["account.move"].browse(
                        account_move.account_move_id
                    )
                    account_move_id.write(
                        {
                            "payment_state": "paid",
                            "invoice_user_id": request.env.user.id,
                            "amount_residual_signed": 0,
                        }
                    )

            except Exception as e:
                raise ValidationError(f"{_('Uhh oh Unexpected error')}- [{e}]")

    @api.onchange("amount")
    def _onchange_amount(self):
        amount = self.env.context.get("amount_total")
        tax_amount = self.env.context.get("tax_amount")
        invoice_line_command = self.env.context.get("invoice_lines")
        account_move_id = self.env.context.get("account_move_id")
        try:
            rem = ""
            if (
                invoice_line_command
                and isinstance(invoice_line_command, list)
                and invoice_line_command[0][0] == 6
            ):
                invoice_line_ids = invoice_line_command[0][2]
                invoice_lines = self.env["account.move.line"].browse(invoice_line_ids)
                if invoice_lines:
                    for inv in invoice_lines:
                        rem += f"{inv.name}, \n"
            for rec in self:
                rec.amount = amount or 0
                rec.tax_amount = tax_amount or 0
                rec.remarks = rem
                rec.transaction_id = str(uuid.uuid4().int)
                rec.account_move_id = account_move_id
        except Exception as e:
            raise ValidationError(f"{_('Internal Server Error')} {e}")

    def action_register_payment_private(self):
        try:
            line_rec=self.env['account.move.line'].sudo().search([('move_id','=',self.env.context.get("account_move_id"))])
            ids_list=self.env.context.get("inv_lines_ids") or []
            min_id = min(ids_list)
            max_id = max(ids_list)
            records = self.env['account.move.line'].search([('id', '>=', min_id), ('id', '<=', max_id)])
            print("records ids",records.ids)
            print("line ids",line_rec.ids)
            return {
                'name': _('Bank/Cheque Payment'),
                'res_model': 'account.payment.register',
                'view_mode': 'form',
                'views': [[False, 'form']],
                'context': {
                    'active_model': 'account.move.line',
                    'active_ids': line_rec.ids,
                },
                'target': 'new',
                'type': 'ir.actions.act_window',
            }
        except Exception as e:
            raise ValidationError(f"{_('Unexpected error occurred!')}-{e}")
    
    def proceed_for_payment(self):
        base_url = request.httprequest.host_url
        amount = self.env.context.get("amount_total")
        tax_amount = self.env.context.get("tax_amount")
        try:
            for rec in self:
                if (
                    rec.payment_method
                    and rec.payment_method.payment_method_name == "esewa"
                ):
                    request.session["esewa_data"] = {
                        "amt": amount,
                        "pid": self.transaction_id,
                        "tAmt": amount,
                        "txAmt": self.tax_amount,
                    }

                    return {
                        "type": "ir.actions.act_url",
                        "url": f"{base_url}redirect-esewa",
                        "target": "new",
                    }

                elif (
                    rec.payment_method
                    and rec.payment_method.payment_method_name == "khalti"
                ):
                    request.session["khalti_data"] = {
                        "amount": amount,
                        "transaction_id": self.transaction_id,
                    }

                    return {
                        "type": "ir.actions.act_url",
                        "url": f"{base_url}khalti-initiate",
                        "target": "new",
                    }
                elif (
                    rec.payment_method
                    and rec.payment_method.payment_method_name == "Cash"
                ):
                    self.payment_status = True
                    self.transaction_date = nepali_datetime.date.today()
                    try:
                        account_move_id = (
                            self.env["account.move"]
                            .sudo()
                            .search([("id", "=", self.account_move_id.id)], limit=1)
                        )
                        account_move_id.write(
                            {
                                "payment_state": "paid",
                                "invoice_user_id": self.env.user.id,
                                "amount_residual_signed": 0,
                            }
                        )
                        return {
                            "effect": {
                                "fadeout": "slow",
                                "message": _('The Cash Payment is Successful.'),
                                "type": "rainbow_man",
                            }
                        }
                    except Exception as e:
                        raise ValidationError(
                            f"{_('Hmm, That Did not Go As Planned! The error you are stumbled upon is -')} {e}"
                        )

                elif (
                    rec.payment_method
                    and rec.payment_method.payment_method_name == "Bank Transfer"
                ):

                    self.payment_status = True
                    self.transaction_date = nepali_datetime.date.today()
                    return self.action_register_payment_private()

                elif (
                    rec.payment_method
                    and rec.payment_method.payment_method_name == "Cheque Deposit"
                ):
                    self.payment_status = True
                    self.transaction_date = nepali_datetime.date.today()
                    return self.action_register_payment_private()
                    
                else:
                    raise ValidationError(
                        f'{_("Payment method ")} [{rec.payment_method.payment_method_name}]{ _(" is not configured.")}'
                    )
        except Exception as e:
            raise ValidationError(f"{_('Internal Server Error')} {e}")
