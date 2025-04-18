#  Copyright 2020 Simone Rubino - Agile Business Group
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from datetime import datetime, timedelta

class AccountFiscalYear(models.Model):
    _name = "account.fiscal.year"
    _description = "Fiscal Year"

    name = fields.Char(
        required=True,
    )
    name_np = fields.Char(
    string="Name in Nepali",
    )
    date_from = fields.Date(
        string="Start Date",
        required=True,
        help="Start Date, included in the fiscal year.",
    )
    date_from_bs = fields.Char(
        string="Start Date",
        help="Start Date, included in the fiscal year.",
        store=True
    )
    date_to = fields.Date(
        string="End Date",
        required=True,
        help="Ending Date, included in the fiscal year.",
    )
    date_to_bs = fields.Char(
        string="End Date",
        help="End Date, included in the fiscal year.",
        store=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.constrains("date_from", "date_to", "company_id")
    def _check_dates(self):
        """Check intersection with existing fiscal years."""
        for fy in self:
            # Starting date must be prior to the ending date
            date_from = fy.date_from
            date_to = fy.date_to
            if date_to < date_from:
                raise ValidationError(
                    _("The ending date must not be prior to the starting date.")
                )

            domain = fy._get_overlapping_domain()
            overlapping_fy = self.search(domain, limit=1)
            if overlapping_fy:
                raise ValidationError(
                    _(
                        "This fiscal year '{fy}' "
                        "overlaps with '{overlapping_fy}'.\n"
                        "Please correct the start and/or end dates "
                        "of your fiscal years."
                    ).format(
                        fy=fy.display_name,
                        overlapping_fy=overlapping_fy.display_name,
                    )
                )

    def _get_overlapping_domain(self):
        """Get domain for finding fiscal years overlapping with self.

        The domain will search only among fiscal years of this company.
        """
        self.ensure_one()
        # Compare with other fiscal years defined for this company
        company_domain = [
            ("id", "!=", self.id),
            ("company_id", "=", self.company_id.id),
        ]

        date_from = self.date_from
        date_to = self.date_to
        # Search fiscal years intersecting with current fiscal year.
        # This fiscal year's `from` is contained in another fiscal year
        # other.from <= fy.from <= other.to
        intersection_domain_from = [
            "&",
            ("date_from", "<=", date_from),
            ("date_to", ">=", date_from),
        ]
        # This fiscal year's `to` is contained in another fiscal year
        # other.from <= fy.to <= other.to
        intersection_domain_to = [
            "&",
            ("date_from", "<=", date_to),
            ("date_to", ">=", date_to),
        ]
        # This fiscal year completely contains another fiscal year
        # fy.from <= other.from (or other.to) <= fy.to
        intersection_domain_contain = [
            "&",
            ("date_from", ">=", date_from),
            ("date_from", "<=", date_to),
        ]
        intersection_domain = expression.OR(
            [
                intersection_domain_from,
                intersection_domain_to,
                intersection_domain_contain,
            ]
        )

        return expression.AND(
            [
                company_domain,
                intersection_domain,
            ]
        )

    def update_fiscal_year(self):
        # Get all companies
        companies = self.env['res.company'].search([])

        for company in companies:
            # Find the current fiscal year for the company
            current_fiscal_year = self.env['account.fiscal.year'].search([
                ('company_id', '=', company.id),
                ('date_from', '<=', fields.Date.today()),
                ('date_to', '>=', fields.Date.today())
            ])

            if current_fiscal_year:
                if current_fiscal_year.date_to == fields.Date.today() and current_fiscal_year.date_from is not fields.Date.today():
                    new_date_from = fields.Date.today().replace(day=fields.Date.today().day+1)
                    new_date_to = (fields.Date.today() + timedelta(days=365)).replace(year=fields.Date.today().year + 1)
                    fiscal_year_name = f"Fiscal Year {fields.Date.today().year}/{fields.Date.today().year+1}"
                    self.env['account.fiscal.year'].create({
                        'company_id': company.id,
                        'date_from': new_date_from,
                        'date_to': new_date_to,
                        'name': fiscal_year_name,
                    })
                    update_cron = self.env['ir.cron'].search([('name', '=', 'Update Fiscal Year')])
                    if update_cron:
                        update_cron.write({'numbercall': 364})
                else:
                    print("Not a suitable date for fiscal year creation for ",company.name)
    

    def _create_default_fiscal_years(self):
        companies = self.env['res.company'].search([])

        reference_date = datetime(2023, 7, 17)

        for company in companies:
            current_date = datetime.now()
            elapsed_days = (current_date - reference_date).days
            elapsed_years = elapsed_days // 365
            fiscal_year_start_date = reference_date + timedelta(days=elapsed_years * 365)
            if current_date < fiscal_year_start_date:
                fiscal_year_start_date = fiscal_year_start_date.replace(year=current_date.year - 1)
            fiscal_year_end_date = fiscal_year_start_date + timedelta(days=363)
            fiscal_year_name = f'Fiscal Year {fiscal_year_start_date.year}/{fiscal_year_end_date.year}'  # Format: 2023/2024

            fiscal_year = self.env['account.fiscal.year'].search([
                ('name', '=', fiscal_year_name),
                ('company_id', '=', company.id),
            ])

            if not fiscal_year:
                self.env['account.fiscal.year'].create({
                    'name': fiscal_year_name,
                    'date_from': fiscal_year_start_date.strftime('%Y-%m-%d'),
                    'date_to': fiscal_year_end_date.strftime('%Y-%m-%d'),
                    'company_id': company.id,
                })
