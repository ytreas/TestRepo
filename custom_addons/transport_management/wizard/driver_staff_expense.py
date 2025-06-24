from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from nepali_datetime import date as nepali_date
import nepali_datetime
from dateutil.relativedelta import relativedelta
from ..models.transport_order import convert_to_bs_date
import io
import base64
import xlsxwriter

# Helper functions
def parse_nepali_date(nepali_date_str):
    nepali_date_str = nepali_date_str.replace('/', '-')
    year, month, day = map(int, nepali_date_str.split('-'))
    return nepali_datetime.date(year, month, day) 

def gregorian_to_nepali(gregorian_date):
    return (gregorian_date.year, gregorian_date.month, gregorian_date.day)

def bs_month_range(env, bs_today=None):
    if bs_today is None:
        greg_today = fields.Date.context_today(env)
        bs_today = nepali_datetime.date.from_datetime_date(greg_today)
    first_bs = bs_today.replace(day=1)
    y, m = first_bs.year, first_bs.month
    if m == 12:
        next_first = nepali_datetime.date(y+1, 1, 1)
    else:
        next_first = nepali_datetime.date(y, m+1, 1)
    last_bs = next_first - timedelta(days=1)
    return first_bs, last_bs

class DriverStaffExpense(models.TransientModel):
    _name = 'driver.staff.expense'
    _description = 'Driver Staff Expense'

    FILTERS = [
        ('date', 'Date Range'),
        ('driver', 'Driver'),
    ]

    NEPALI_MONTHS = {
        1: 'Baishakh', 2: 'Jestha', 3: 'Ashadh',
        4: 'Shrawan', 5: 'Bhadra', 6: 'Ashwin',
        7: 'Kartik', 8: 'Mangsir', 9: 'Poush',
        10: 'Magh', 11: 'Falgun', 12: 'Chaitra',
    }

    filter_by = fields.Selection(FILTERS, string="Filter By", required=True, default='date')
    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")
    date_from_bs = fields.Char(string="From Date (BS)", compute='_compute_bs_date')
    date_to_bs = fields.Char(string="To Date (BS)", compute='_compute_bs_date')
    driver_id = fields.Many2one('driver.details', string="Driver",
                                domain=[('available','=',True)])
    trips_count = fields.Integer(
        string="Number of Trips", 
        help="Computed number of assignments for this driver in the period"
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_("From Date cannot be after To Date."))

    @api.constrains('date_from', 'date_to')
    def _check_future_dates(self):
        today = fields.Date.today()
        for record in self:
            if record.date_from and record.date_from > today:
                raise UserError(_("Start date cannot be in the future."))
            if record.date_to and record.date_to > today:
                raise UserError(_("End date cannot be in the future."))

    @api.depends('date_from', 'date_to')
    def _compute_bs_date(self):
        for rec in self:
            rec.date_from_bs = convert_to_bs_date(rec.date_from)
            rec.date_to_bs = convert_to_bs_date(rec.date_to)

    def _get_report_data(self):
        """Common method to fetch and process report data."""
        self.ensure_one()
        report_data = []

        # Get all drivers or just the selected one
        if self.driver_id:
            drivers = self.env['driver.details'].browse(self.driver_id.id)
        else:
            drivers = self.env['driver.details'].search([])

        # Get date range in BS
        first_bs, last_bs = bs_month_range(self)
        month_number = first_bs.month
        month_name = self.NEPALI_MONTHS.get(month_number, 'Unknown')

        for driver in drivers:
            try:
                if not driver.employee_id:
                    print(f"Warning: Driver {driver.name} is not linked to an employee record")
                    continue

                domain = [('driver_id', '=', driver.id)]
                if self.date_from and self.date_to:
                    domain += [
                        ('assigned_date', '>=', self.date_from),
                        ('assigned_date', '<=', self.date_to),
                    ]

                print("Domain for driver:", domain)
                trip_count = self.env['transport.assignment'].search_count(domain)
                print(f"Trip count for driver {driver.name}: {trip_count}")

                employee = driver.employee_id
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', employee.id),
                ], limit=1)

                if not contract:
                    print(f"Warning: No active contract found for driver {driver.name}")
                    continue

                payslip = self.env['hr.payslip'].search([
                    ('employee_id', '=', employee.id),
                ], limit=1)

                if not payslip or not payslip.batches_id:
                    print(f"Warning: No payslip or salary batch found for {driver.name}")
                    continue

                salary_batch = payslip.batches_id
                monthly_detail = self.env['montly.employee.detail'].search([
                    ('batch_id', '=', salary_batch.id),
                    ('employee_name', '=', employee.id)
                ], limit=1)

                if not monthly_detail:
                    print(f"Warning: No monthly detail record found for {driver.name}")
                    continue

                batch_months = salary_batch.months
                month_match = False
                for batch_month in batch_months:
                    if int(batch_month.code) == month_number:
                        month_match = True
                        break

                if not month_match:
                    print(f"Warning: Month mismatch for driver {driver.name}")
                    continue

                report_data.append({
                    'employee_name': employee.name,
                    'month_label': f"{month_name} {first_bs.year}",
                    'trips_count': trip_count,
                    'transport_allowance': monthly_detail.transport_allowance,
                    'overtime_allowance': 0,
                    'basic_salary': monthly_detail.starting_salary,
                    'deduction': monthly_detail.total_deduction,
                    'net_payable': monthly_detail.total_total,
                })
                print("Report data for driver:", report_data[-1])

            except Exception as e:
                print(f"Error processing driver {driver.name}: {str(e)}")
                continue

        if not report_data:
            raise UserError(_("No valid data found for the selected criteria."))

        return report_data

    def print_report(self):
        """Generate PDF report."""
        report_data = self._get_report_data()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'transport_management.driver_expense_summary_report',
            'report_type': 'qweb-pdf',
            'context': dict(
                self.env.context,
                date_from=self.date_from_bs,
                date_to=self.date_to_bs,
                report_data=report_data,
            ),
        }

    def export_to_excel(self):
        """Generate and download Excel report."""
        self.ensure_one()
        report_data = self._get_report_data()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Driver Staff Expense")

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F0F0F0',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        number_format = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0.00'
        })

        # Set column widths
        worksheet.set_column('A:A', 25)  # Employee Name
        worksheet.set_column('B:B', 15)  # Month
        worksheet.set_column('C:C', 12)  # Trips
        worksheet.set_column('D:H', 15)  # Financial columns

        # Write headers
        headers = [
            "कर्मचारीको नाम (Employee Name)",
            "महिना (Month)",
            "ट्रिप संख्या (Trips)",
            "यातायात भत्ता (Transport)",
            "ओभरटाइम भत्ता (Overtime)",
            "आधारभूत तलब (Basic)",
            "कटौती (Deduction)",
            "खुद भुक्तानी (Net)"
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data
        total_net = 0
        for row, data in enumerate(report_data, start=1):
            worksheet.write(row, 0, data['employee_name'], cell_format)
            worksheet.write(row, 1, data['month_label'], cell_format)
            worksheet.write(row, 2, data['trips_count'], cell_format)
            worksheet.write(row, 3, data['transport_allowance'], number_format)
            worksheet.write(row, 4, data['overtime_allowance'], number_format)
            worksheet.write(row, 5, data['basic_salary'], number_format)
            worksheet.write(row, 6, data['deduction'], number_format)
            worksheet.write(row, 7, data['net_payable'], number_format)
            total_net += data['net_payable']

        # Write total row
        total_row = len(report_data) + 1
        total_format = workbook.add_format({
            'bold': True,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#fafafa',
            'num_format': '#,##0.00'
        })
        
        worksheet.write(total_row, 0, "जम्मा (Total)", total_format)
        for col in range(1, 7):
            worksheet.write_blank(total_row, col, None, total_format)
        worksheet.write(total_row, 7, total_net, total_format)

        workbook.close()
        
        # Get the Excel content
        excel_data = output.getvalue()
        output.close()

        # Generate filename with date range
        filename = f"Driver_Staff_Expense_{self.date_from or ''}_to_{self.date_to or ''}.xlsx"

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/binary/download_and_delete/{attachment.id}',
            'target': 'self',
        }