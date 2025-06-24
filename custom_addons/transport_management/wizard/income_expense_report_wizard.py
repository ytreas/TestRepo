from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.transport_order import convert_to_bs_date
import io
import base64
import xlsxwriter

class IncomeExpenseReportWizard(models.TransientModel):
    _name = 'income.expense.report.wizard'
    _description = 'Income Expense Report Wizard'

    filter_by = fields.Selection([
        ('date', 'Date Range'),
        ('vehicle', 'Vehicle'),
    ], string="Filter By", required=True, default='date')

    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")
    date_from_bs = fields.Char(string='Date From (BS)', compute='_compute_bs_date', store=True)
    date_to_bs = fields.Char(string='Date To (BS)', compute='_compute_bs_date', store=True)
    vehicle_id = fields.Many2one('vehicle.number', string="Truck (Vehicle)",
                                 domain=[
                                        ('available', '=', True),
                                        '|',
                                            ('heavy', 'in', ['truck', 'mini_truck']),
                                            ('vehicle_type.vehicle_type', '=', 'heavy'),
                                    ])
    department = fields.Char(string="Department/Unit", default="Transport Division")
    authorized_by = fields.Char(string="Authorized By", default="Transport Manager")

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
            rec.date_from_bs = convert_to_bs_date(rec.date_from) if rec.date_from else ''
            rec.date_to_bs = convert_to_bs_date(rec.date_to) if rec.date_to else ''

    def _get_report_data(self):
        """Common method to fetch and process report data."""
        self.ensure_one()

        domain = []
        if self.filter_by == 'date':
            if not self.date_from or not self.date_to:
                raise UserError(_("Please select Date From and Date To."))
            domain += [('scheduled_date_from', '>=', self.date_from),
                      ('scheduled_date_to', '<=', self.date_to)]
        elif self.filter_by == 'vehicle':
            if not self.vehicle_id:
                raise UserError(_("Please select a Truck (Vehicle)."))
            domain.append(('assigned_truck_id', '=', self.vehicle_id.id))
        vehicle_domain = domain + [
            ('assigned_truck_id.available', '=', True),
            '|',
                ('assigned_truck_id.heavy', 'in', ['truck', 'mini_truck']),
                ('assigned_truck_id.vehicle_type.vehicle_type', '=', 'heavy'),
        ]
        print("Vehicle domain", vehicle_domain)

        orders = self.env['transport.order'].search(vehicle_domain)
        print("Orders found:", orders)

        date_from = self.date_from
        date_to = self.date_to
        if date_from and date_to:
            date_from_bs = convert_to_bs_date(date_from)
            date_to_bs = convert_to_bs_date(date_to)
            print("Date From:", date_from_bs)
            print("Date To:", date_to_bs)

        data_list = []
        for rec in orders:
            income = rec.total_service_charge or 0.0
            fuel = rec.fuel_expense or 0.0
            toll = rec.toll_expense or 0.0
            allowance = rec.driver_allowance_expense or 0.0
            maintenance = rec.maintenance_expense or 0.0
            profit_loss = income - (fuel + toll + allowance + maintenance)

            data_list.append({
                'trip_no': rec.name,
                'truck_no': rec.assigned_truck_id.final_number or '',
                'income': income,
                'fuel_cost': fuel,
                'toll_cost': toll,
                'allowance': allowance,
                'maintenance_cost': maintenance,
                'profit_loss': profit_loss,
            })
        
        print("Report Data Prepared:", data_list)
        return data_list

    def print_report(self):
        """Generate PDF report."""
        report_data = self._get_report_data()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'transport_management.income_expense_report_template',
            'report_type': 'qweb-pdf',
            'print_report_name': 'Income_Expense_Report',
            'context': dict(self.env.context, 
                          income_expense_data=report_data,
                          date_from=self.date_from_bs,
                          date_to=self.date_to_bs,
                          prepared_by=self.env.user.name or 'N/A',
                          prepared_by_designation=self.env.user.job_title or 'N/A',
                          authorized_by=self.authorized_by or 'N/A',
                          department= self.department or 'N/A',
                          report_name = 'Income Expense Report',
                          filter_by=self.filter_by or 'N/A',
                          date_bs = convert_to_bs_date(fields.Date.today()) or 'N/A',
                          )
        }

    def export_to_excel(self):
        """Generate and download Excel report."""
        self.ensure_one()
        report_data = self._get_report_data()

        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Income Expense Report")

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
        worksheet.set_column('A:A', 15)  # Trip No
        worksheet.set_column('B:B', 20)  # Truck No
        worksheet.set_column('C:H', 15)  # Financial columns

        # Write headers
        headers = [
            "ट्रिप नं. (Trip No.)",
            "ट्रक नं. (Truck No.)",
            "आम्दानी (Income)",
            "इन्धन खर्च (Fuel Cost)",
            "टोल खर्च (Toll Cost)",
            "भत्ता (Allowance)",
            "मर्मत खर्च (Maintenance)",
            "नाफा/नोक्सान (Profit/Loss)"
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data
        total_profit_loss = 0
        for row, data in enumerate(report_data, start=1):
            worksheet.write(row, 0, data['trip_no'], cell_format)
            worksheet.write(row, 1, data['truck_no'], cell_format)
            worksheet.write(row, 2, data['income'], number_format)
            worksheet.write(row, 3, data['fuel_cost'], number_format)
            worksheet.write(row, 4, data['toll_cost'], number_format)
            worksheet.write(row, 5, data['allowance'], number_format)
            worksheet.write(row, 6, data['maintenance_cost'], number_format)
            worksheet.write(row, 7, data['profit_loss'], number_format)
            total_profit_loss += data['profit_loss']

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
        worksheet.write_blank(total_row, 1, None, total_format)
        worksheet.write_blank(total_row, 2, None, total_format)
        worksheet.write_blank(total_row, 3, None, total_format)
        worksheet.write_blank(total_row, 4, None, total_format)
        worksheet.write_blank(total_row, 5, None, total_format)
        worksheet.write_blank(total_row, 6, None, total_format)
        worksheet.write(total_row, 7, total_profit_loss, total_format)

        workbook.close()
        
        # Get the Excel content
        excel_data = output.getvalue()
        output.close()

        # Generate filename with date range
        filename = f"Income_Expense_Report_{self.date_from or ''}_to_{self.date_to or ''}.xlsx"

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })

        # Return the download action with custom URL
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/binary/download_and_delete/{attachment.id}',
            'target': 'self',
        }