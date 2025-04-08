from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import nepali_datetime
from datetime import datetime
import datetime
import calendar
import secrets
import requests


class RegistrationRenew(models.Model):
    _name = "organization.register.renew"

    type = fields.Selection(
        [("registration", "Registration"), ("renew", "Renew")],
        string="Payment For",
        required=True,
    )
    organization_type = fields.Selection(
        [
            ("upabhokta_samiti", "Upabhokta Samiti"),
            ("organization", "Organization"),
            ("tole_bikash_sanstha", "Tole Bikash sanstha"),
            ("class_d", "Class D"),
        ],
        default="organization",
        required=True,
    )
    # Visible only if renew
    upabhokta_registration_number = fields.Many2one(
        "upabhokta.samiti.master", "Registration Number"
    )
    organization_registration_number = fields.Many2one(
        "organization.master", "Registration Number"
    )
    tole_bikash_registration_number = fields.Many2one(
        "tole.bikash.master", "Registration Number"
    )

    # Visible if new registration
    upabhokta_samiti_contact_person = fields.Many2one(
        "res.users",
        "Contact Person Email",
        domain="[('upabhokta_samiti_category','=',3)]",
    )
    organization_contact_person = fields.Many2one(
        "res.users",
        "Contact Person Email",
        domain="[('upabhokta_samiti_category','=',1)]",
    )
    tole_bikash_contact_person = fields.Many2one(
        "res.users",
        "Contact Person Email",
        domain="[('upabhokta_samiti_category','=',4)]",
    )

    fiscal_year = fields.Selection(selection="get_fiscal_years", string="Fiscal Year")
    rate_titles = fields.Many2many(
        "fiscal.wise.rate.setup", domain="[('fiscal_year','=',fiscal_year)]"
    )
    rates_amount = fields.Char("Total Rate Amount", compute="_get_rate_amount")
    fine_title = fields.Many2many(
        "fiscal.wise.fine.discount",
        relation="org_reg_renew_fine_title_rel",
        domain="[('fiscal_year','=',fiscal_year),('discount_or_fine','=','fine'),('to_category','=',organization_type)]",
    )
    fine_amount = fields.Char("Total Fine Amount", compute="_get_fine_amount")

    discount_title = fields.Many2many(
        "fiscal.wise.fine.discount",
        relation="org_reg_renew_dis_title_rel",
        domain="[('fiscal_year','=',fiscal_year),('discount_or_fine','=','discount'),('to_category','=',organization_type)]",
    )
    discount_amount = fields.Char(
        "Total Discount Amount", compute="_get_discount_amount"
    )
    total_cost = fields.Float("Total Cost", compute="_compute_total_cost", store=True)
    total_renewal_cost = fields.Float("Total Cost")

    last_renewal_date = fields.Char(
        "last Renewal date", compute="_compute_last_renewal_date"
    )
    dynamic_fiscal_years = fields.Char(
        string="Fiscal Years", selection="_compute_dynamic_fiscal_years"
    )
    result_field = fields.Text("Result")
    payment_token=fields.Char("Payment Token")
    
    
    def get_fiscal_years(self):
        _date = nepali_datetime.date.today()
        _year = _date.year
        fiscal_years_arr = []

        start_year = 2001
        end_year = int(_year) + 1
        for year in range(start_year, end_year):
            fiscal_year = f"{year}/{year + 1}"
            fiscal_years_arr.append((fiscal_year, fiscal_year))
        return fiscal_years_arr[::-1]        
        
    # TODO: calculate the final amount by subtracting the license and discount percentage
    @api.depends("rate_titles")
    def _get_rate_amount(self):
        _total_rate = 0.00
        for rec in self:
            for rt in rec.rate_titles:
                _total_rate += float(rt.rate)

        self.rates_amount = _total_rate

    @api.depends("fine_title", "rates_amount")
    def _get_fine_amount(self):
        for rec in self:
            _total_fine = 0.0
            for rt in rec.fine_title:
                print(rec.fine_title)

                if rt.fine_amount:
                    _total_fine += float(rt.fine_amount)

                else:

                    _total_fine += (
                        float(rt.fine_percentage) * float(rec.rates_amount)
                    ) / 100

            self.fine_amount = _total_fine

    @api.depends("discount_title")
    def _get_discount_amount(self):
        _total_discount = 0.00
        for rec in self:
            for rt in rec.discount_title:
                if rt.fine_amount:
                    _total_discount += float(rt.fine_amount)
                else:

                    _total_discount += (
                        float(rt.fine_percentage) * float(rec.rates_amount)
                    ) / 100

            self.discount_amount = _total_discount

    @api.depends("rates_amount", "fine_amount", "discount_amount")
    def _compute_total_cost(self):
        for rec in self:
            rates_amount = float(rec.rates_amount) if rec.rates_amount else 0.0
            fine_amount = float(rec.fine_amount) if rec.fine_amount else 0.0
            discount_amount = float(rec.discount_amount) if rec.discount_amount else 0.0

            # Compute total_cost
            total_cost = rates_amount + fine_amount - discount_amount
            rec.total_cost = total_cost

    @api.depends(
        "organization_type",
        "upabhokta_registration_number",
        "organization_registration_number",
        "tole_bikash_registration_number",
    )
    def _compute_last_renewal_date(self):

        for rec in self:
            registration_number = False
            if self.organization_type == "upabhokta_samiti":
                registration_number = self.upabhokta_registration_number.id
            elif self.organization_type in ["organization", "class_d"]:
                registration_number = self.organization_registration_number.id
            elif self.organization_type == "tole_bikash_sanstha":
                registration_number = self.tole_bikash_registration_number.id
            # Search for the last payment record for the organization type and registration number
            last_payment = self.env["organization.payment.master"].search(
                [
                    ("organization_type", "=", rec.organization_type),
                    ("payment_for", "=", "renew"),
                    ("organization_registration_number", "=", registration_number),
                    ("payment_status", "=", True),
                ],
                order="transaction_date desc",
                limit=1,
            )
            print(last_payment)

            if last_payment:
                transaction_date = datetime.datetime.strptime(
                    last_payment.transaction_date, "%Y-%m-%d"
                )
                last_renewal_date = transaction_date.year
                rec.last_renewal_date = last_renewal_date
            else:
                rec.last_renewal_date = False

    def nepali_to_english_date(self, nepali_year):
        english_year = (
            nepali_year - 57 if datetime.date.today().month < 4 else nepali_year - 56
        )
        start_date = datetime.date(english_year, 7, 16)
        end_date = datetime.date(english_year + 1, 8, 15)

        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    @api.onchange("last_renewal_date", "fiscal_year")
    def _compute_dynamic_fiscal_years(self):
        result_array = []
        for rec in self:
            if not rec.last_renewal_date or not rec.fiscal_year:
                rec.dynamic_fiscal_years = []
                return

            last_renewal_year = rec.last_renewal_date
            fiscal_year_start, fiscal_year_end = rec.fiscal_year.split("/")
            today_date = datetime.date.today().strftime("%Y-%m-%d")
            start_year = int(last_renewal_year[:4])
            end_year = int(fiscal_year_start[:4])

            dynamic_fiscal_years = [year for year in range(start_year, end_year + 1)]
            rec.dynamic_fiscal_years = dynamic_fiscal_years

            total_amount = 0.0

            for year in dynamic_fiscal_years:

                fiscal_year_str = f"{year}/{year + 1}"
                english_start_date, english_end_date = self.nepali_to_english_date(year)
                fiscal_year_fine = self.env["fiscal.wise.fine.discount"].search(
                    [("fiscal_year", "=", fiscal_year_str)], limit=1
                )

                if fiscal_year_fine:
                    fiscal_rate = self.env["fiscal.wise.rate.setup"].search(
                        [("fiscal_year", "=", fiscal_year_str)], limit=1
                    )
                    rate = float(fiscal_rate.rate)
                    rate_cost = rate
                    english_start_day = datetime.datetime.strptime(
                        english_start_date, "%Y-%m-%d"
                    )
                    start_year = english_start_day.year
                    start_month = english_start_day.month
                    start_day = english_start_day.day
                    fine_year = int(fiscal_year_fine.year)
                    fine_month = int(fiscal_year_fine.month)
                    fine_day = int(fiscal_year_fine.day)
                    evaluation_year = start_year + fine_year
                    evaluation_month = start_month + fine_month
                    evaluation_day = start_day + fine_day
                    while evaluation_month > 12:
                        evaluation_year += 1
                        evaluation_month -= 12

                    while (
                        evaluation_day
                        > calendar.monthrange(evaluation_year, evaluation_month)[1]
                    ):
                        evaluation_day -= calendar.monthrange(
                            evaluation_year, evaluation_month
                        )[1]
                        evaluation_month += 1
                        if evaluation_month > 12:
                            evaluation_year += 1
                            evaluation_month -= 12
                    evaluation_date = datetime.datetime(
                        evaluation_year, evaluation_month, evaluation_day
                    ).strftime("%Y-%m-%d")
                    fine_amount = 0
                    discount_amount = 0
                    print(fiscal_year_fine.fine_amount)
                    print(fiscal_year_fine.fine_percentage)
                    if evaluation_date <= today_date:
                        print("processing")
                        if fiscal_year_fine.discount_or_fine == "fine":
                            print("entered to fine")
                            print(fiscal_year_fine.fine_amount)
                            print(fiscal_year_fine.fine_percentage)
                            if fiscal_year_fine.fine_amount:
                                print("entered to fine Amount")
                                fine_amount = float(fiscal_year_fine.fine_amount)
                                print(
                                    f"fiscal year fine amount - {fiscal_year_fine.fine_amount}"
                                )
                                rate += fine_amount
                                print(f"rate amount {rate}")
                            elif fiscal_year_fine.fine_percentage:
                                print("entered to fine Percentage")
                                fine_percentage = float(
                                    fiscal_year_fine.fine_percentage
                                )
                                print(
                                    f"fiscal year fine amount - {fiscal_year_fine.fine_percentage}"
                                )
                                fine_amount = (fine_percentage * rate) / 100
                                rate += fine_amount
                                print(f"rate percentage {rate}")

                        elif fiscal_year_fine.discount_or_fine == "discount":
                            print("entered to Discount")
                            if fiscal_year_fine.fine_amount:
                                print("entered to Discount Amount")
                                discount_amount = float(fiscal_year_fine.fine_amount)
                                rate -= discount_amount
                            elif fiscal_year_fine.fine_percentage:
                                print("entered to Discount Amount")
                                discount_percentage = float(
                                    fiscal_year_fine.fine_percentage
                                )
                                discount_amount = (discount_percentage * rate) / 100
                                rate -= discount_amount
                    else:
                        rate = rate

                    total_cost = rate
                    print(f"total cost {total_cost}")
                    total_amount += total_cost
                    self.total_renewal_cost = total_amount

                    # Append details for the fiscal year to the result array
                    result_array.append(
                        {
                            "Fiscal Year": fiscal_year_str,
                            "Rate": rate_cost,
                            "Fine Amount": fine_amount,
                            "Discount Amount": discount_amount,
                            "Total Cost after Fine or Discount": rate,
                        }
                    )

            result_array.append(
                {"Total Amount": total_amount, "Today Date": today_date}
            )
        result_string = "\n".join(
            [
                f"{key}: {value}"
                for result in result_array
                for key, value in result.items()
            ]
        )

        self.result_field = result_string
        
    def save_data_to_payment_master(self):
        registration_number = False
        remarks = ""
        client_id = False

        if self.organization_type == "upabhokta_samiti":
            registration_number = self.upabhokta_registration_number.id
        elif self.organization_type in ["organization", "class_d"]:
            registration_number = self.organization_registration_number.id
        elif self.organization_type == "tole_bikash_sanstha":
            registration_number = self.tole_bikash_registration_number.id

        if self.organization_type == "upabhokta_samiti":
            client_id = self.upabhokta_samiti_contact_person.id
        elif self.organization_type in ["organization", "class_d"]:
            client_id = self.organization_contact_person.id
        elif self.organization_type == "tole_bikash_sanstha":
            client_id = self.tole_bikash_contact_person.id

        if self.type == "registration":
            amount = self.total_cost
            remarks = "Registration Fee"
        elif self.type == "renew":
            amount = self.total_renewal_cost
            if not self.result_field:
                remarks = "Registration Fee"
            else:
                remarks = self.result_field

        org_payment_master = self.env["organization.payment.master"].sudo().search([])

        if client_id:
            response = org_payment_master.sudo().create(
                {
                    "organization_type": self.organization_type,
                    "transaction_date": datetime.date.today(),
                    "organization_registration_number": registration_number,
                    "payment_for": self.type,
                    "amount": amount,
                    "token": secrets.token_hex(8),
                    "client_id": client_id,
                    "payment_status": False,
                    "remarks": remarks,
                }
            )
            
            self.payment_token=response.token
            
            return response
        else:
            raise ValidationError("The client Id is required.")
