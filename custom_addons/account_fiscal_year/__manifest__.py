# Copyright 2016 Camptocamp SA
# Copyright 2018 Lorenzo Battistini <https://github.com/eLBati>
# Copyright 2020 Simone Rubino - Agile Business Group
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Account Fiscal Year",
    "summary": "Create Account Fiscal Year",
    "version": "17.0",
    "development_status": "Production/Stable",
    "category": "Accounting",
    "website": "https://github.com/OCA/account-financial-tools",
    "author": "Agile Business Group, Camptocamp SA, "
    "Odoo Community Association (OCA)",
    "maintainers": ["eLBati"],
    "license": "AGPL-3",
    "depends": [
        "account","purchase","sale"
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/account_fiscal_year_rule.xml",
        "views/account_fiscal_year_views.xml",
        "views/inherit_fiscal.xml",
        "data/fiscal_year_cron_data.xml",
    ],
}
