from odoo import models, api
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        """Override create method to load COA from XML file for the new company."""
        company = super(ResCompany, self).create(vals)

        try:
            self._load_coa(company)
        except Exception as e:
            raise UserError(f"Error loading Chart of Accounts: {e}")

        return company

    def _load_coa(self, company):
        """Load all COA data from XML file."""
        try:
            # Find all account records in the 'base_accounting_kit' module
            model_data_records = self.env['ir.model.data'].search([
                ('module', '=', 'base_accounting_kit'),
                ('model', '=', 'account.account'),
            ])
            
            for record in model_data_records:
                try:
                    # Use the record name to get the XML ID
                    account_template = self.env.ref(f"{record.module}.{record.name}")
                    # Copy the account template to create a new account for the company
                    account_template.copy({'company_id': company.id})
                except Exception as e:
                    raise UserError(f"Error loading account {record.name}: {e}")

        except Exception as e:
            raise UserError(f"Error loading COA from XML: {e}")
