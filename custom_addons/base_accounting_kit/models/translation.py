import requests
from odoo import models, api,fields


class TranslationServiceMixin(models.Model):
    _name = "translation.service.mixin"
    _description = "Translation Service Mixin"
    
    translation_enabled=fields.Boolean("Enable translation",default=True)

    def translate_to_english(self, text):
        """Translate the given text to English if it's in Nepali."""
        
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ne&tl=en&dt=t&q={requests.utils.quote(text)}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                result = response.json()
                translated_text = result[0][0][0]  
                return translated_text
            else:
                return text  
        except requests.exceptions.RequestException:
            return text


class InheritStockPicking(TranslationServiceMixin, models.Model):
    _inherit = "product.template"

    @api.onchange("name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)


class InheritAccountFiscalYear(TranslationServiceMixin, models.Model):
    _inherit = "account.fiscal.year"

    @api.onchange("name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)


class InheritProductProduct(TranslationServiceMixin, models.Model):
    _inherit = "product.product"

    @api.onchange("name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)


# class InheritResPartnerTran(TranslationServiceMixin, models.Model):
#     _inherit = "product.product"

#     @api.onchange("name_np")
#     def tran_origin(self):
#         translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
#         if translation_enabled.translation_enabled and self.name_np:
#             self.complete_name = self.translate_to_english(self.name_np)


class InheritCRMTeamTran(TranslationServiceMixin, models.Model):
    _inherit = "crm.team"

    @api.onchange("name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)


class InheritAccountJournalTran(TranslationServiceMixin, models.Model):
    _inherit = "account.journal"

    @api.onchange("name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)


class InheritLocationProvinceTran(TranslationServiceMixin, models.Model):
    _inherit = "location.province"

    @api.onchange("name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)


class InheritCompanyCategoryTran(TranslationServiceMixin, models.Model):
    _inherit = "company.category"

    @api.onchange("name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)


class InheritResUserTran(TranslationServiceMixin, models.Model):
    _inherit = "res.users"

    @api.onchange("name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)


class InheritCompanyTran(TranslationServiceMixin, models.Model):
    _inherit = "res.company"

    @api.onchange("name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)
            
    @api.onchange("owner_name_np")
    def tran_owner_name_np(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.owner_name_np:
            self.owner_name_en = self.translate_to_english(self.owner_name_np)

class InheritPartnerTran(TranslationServiceMixin, models.Model):
    _inherit = "res.partner"

    @api.onchange("name_np")
    def tran_origin(self):
        print("translation")
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)

    @api.model_create_multi
    def create(self, vals_list):   
        records = super().create(vals_list)

        for record in records:
            if record.name_np:
                record.with_context(lang='ne_NP').write({
                    'name': record.name_np
                })
        
        return records
    
    def write(self, vals):
        res = super().write(vals)
        if 'name_np' in vals:
            for record in self:
                if record.name_np:
                    record.with_context(lang='ne_NP').write({
                        'name': record.name_np
                    })
        return res
            
class InheritIssuerBankTran(TranslationServiceMixin, models.Model):
    _inherit = "issuer.bank"

    @api.onchange("bank_name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if  translation_enabled.translation_enabled and self.bank_name_np:
            self.bank_name_en = self.translate_to_english(self.bank_name_np)
            
class InheritBranchBankTran(TranslationServiceMixin, models.Model):
    _inherit = "branch.bank"    

    @api.onchange("branch_name_np")
    def tran_origin(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if  translation_enabled.translation_enabled and self.branch_name_np:
            self.branch_name = self.translate_to_english(self.branch_name_np)


                
class InheritUOMCategory(TranslationServiceMixin,models.Model):
    _inherit="uom.category"
    
    name_np=fields.Char('Unit of Measure Category(NP)')
    @api.onchange("name_np")
    def trans_uom(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if  translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)
            
class InheritUOMCategory(TranslationServiceMixin,models.Model):
    _inherit = 'uom.uom'
    
    # name_np=fields.Char('Unit of Measure(NP)')
    @api.onchange("name_np")
    def trans_uom(self):
        translation_enabled=self.env['translation.service.mixin'].sudo().search([],limit=1)
        if  translation_enabled.translation_enabled and self.name_np:
            self.name = self.translate_to_english(self.name_np)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        # Set translations using context
        for record in records:
            if record.name_np:
                record.with_context(lang='ne_NP').write({
                    'name': record.name_np
                })
        
        return records
    
    def write(self, vals):
        res = super().write(vals)
        if 'name_np' in vals:
            for record in self:
                if record.name_np:
                    record.with_context(lang='ne_NP').write({
                        'name': record.name_np
                    })
        return res
    # class ResUser(models.Model):
    #     _inherit = 'res.users'

    #     @api.onchange('lang')
    #     def _onchange_language_code(self):
    #         if self.env.user and self.env.user.company_id:
    #             company = self.env.user.company_id
    #             if self.lang == 'en_US':
    #                 company.font = 'Lato'
    #             elif self.lang == 'ne_NP':
    #                 company.font = 'Kalimati'
