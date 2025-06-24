from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from ..models.transport_order import convert_to_bs_date
import io
import base64
import xlsxwriter

class ServiceExecutionReportWizard(models.TransientModel):
    _name = 'service.execution.report.wizard'
    _description = 'Service Execution Report Wizard'

    FILTERS = [
        ('date', 'Date Range'),
        ('vehicle', 'Vehicle'),
        ('service_type', 'Service Type'),
        ('provider', 'Service Provider'),
    ]

    filter_by = fields.Selection(FILTERS, string="Filter By", required=True, default='date')
    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")
    date_from_bs = fields.Char(string='Date From (BS)', compute='_compute_bs_date', store=True)
    date_to_bs = fields.Char(string='Date To (BS)', compute='_compute_bs_date', store=True)
    vehicle_id = fields.Many2one('vehicle.number', string="Vehicle",
                                 domain=[
                                        ('available', '=', True),
                                        '|',
                                            ('heavy', 'in', ['truck', 'mini_truck']),
                                            ('vehicle_type.vehicle_type', '=', 'heavy'),
                                    ])
    service_type = fields.Char(string="Service Type")
    service_provider = fields.Char(string="Service Provider")

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
        print("Generating report with filter:", self.filter_by)

        domain = []
        if self.filter_by == 'date':
            if not (self.date_from and self.date_to):
                raise UserError(_("Please set both From Date and To Date."))
            domain = [
                ('start_time', '>=', self.date_from),
                ('start_time', '<=', self.date_to),
            ]
        elif self.filter_by == 'vehicle':
            if not self.vehicle_id:
                raise UserError(_("Please select a Vehicle."))
            domain = [('vehicle_id', '=', self.vehicle_id.id)]
        elif self.filter_by == 'service_type':
            if not self.service_type:
                raise UserError(_("Please enter a Service Type."))
            domain = [('execution_line_id.name.name', 'ilike', self.service_type)]
        elif self.filter_by == 'provider':
            if not self.service_provider:
                raise UserError(_("Please enter a Service Provider."))
            domain = [('service_provider', 'ilike', self.service_provider)]
        print("Search domain:", domain)
        extra_domain = [
            ('vehicle_id.available', '=', True),
            '|',
            ('vehicle_id.heavy', 'in', ['truck', 'mini_truck']),
            ('vehicle_id.vehicle_type.vehicle_type', '=', 'heavy'),
        ]
        print("Extra domain:", extra_domain)
        full_domain = domain + extra_domain
        print("Full domain:", full_domain)

        records = self.env['service.execution'].search(full_domain)
        print(f"Found {len(records)} records")

        data = []
        total_amount = 0
        for rec in records:
            # Get service names from the execution lines
            service_names = [line.name.name.name for line in rec.execution_line_id]
            print(f"Processing record {rec.id} with services: {service_names}")

            start_time_bs = convert_to_bs_date(rec.start_time)
            next_service_date_bs = convert_to_bs_date(rec.next_service_date)

            row_data = {
                'date': start_time_bs,
                'truck_no': rec.vehicle_id.final_number,
                'service_type': ', '.join(service_names),  # Join the list of service names
                'provider': rec.service_provider,
                'invoice_no': rec.invoice_no or '',
                'amount': rec.cost_incurred,
                'next_service': next_service_date_bs,
                'remarks': rec.service_quality_feedback or '',
            }
            data.append(row_data)
            total_amount += rec.cost_incurred
            print(f"Added row: {row_data}")

        print(f"Total records processed: {len(data)}")
        print(f"Total amount: {total_amount}")
        return data, total_amount

    def print_report(self):
        """Generate PDF report."""
        report_data, total_amount = self._get_report_data()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'transport_management.service_execution_report_template',
            'report_type': 'qweb-pdf',
            'context': dict(
                self.env.context,
                date_from=self.date_from_bs,
                date_to=self.date_to_bs,
                records=report_data,
                total_amount=total_amount
            ),
        }

    def export_to_excel(self):
        """Generate and download Excel report."""
        self.ensure_one()
        report_data, total_amount = self._get_report_data()

        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Service Execution Report")

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
        worksheet.set_column('A:A', 15)  # Date
        worksheet.set_column('B:B', 20)  # Truck No
        worksheet.set_column('C:C', 30)  # Service Type
        worksheet.set_column('D:D', 20)  # Provider
        worksheet.set_column('E:E', 15)  # Invoice No
        worksheet.set_column('F:F', 15)  # Amount
        worksheet.set_column('G:G', 15)  # Next Service
        worksheet.set_column('H:H', 25)  # Remarks

        # Write headers
        headers = [
            "मिति (Date)",
            "ट्रक नं. (Truck No.)",
            "सेवाको किसिम (Service Type)",
            "सेवा प्रदायक (Provider)",
            "बिल नं. (Invoice No.)",
            "रकम (Amount)",
            "अर्को सेवा (Next Service)",
            "कैफियत (Remarks)"
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data
        for row, data in enumerate(report_data, start=1):
            worksheet.write(row, 0, data['date'], cell_format)
            worksheet.write(row, 1, data['truck_no'], cell_format)
            worksheet.write(row, 2, data['service_type'], cell_format)
            worksheet.write(row, 3, data['provider'], cell_format)
            worksheet.write(row, 4, data['invoice_no'], cell_format)
            worksheet.write(row, 5, data['amount'], number_format)
            worksheet.write(row, 6, data['next_service'], cell_format)
            worksheet.write(row, 7, data['remarks'], cell_format)

        # Write total
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
        worksheet.write(total_row, 5, total_amount, total_format)
        worksheet.write_blank(total_row, 6, None, total_format)
        worksheet.write_blank(total_row, 7, None, total_format)

        workbook.close()
        
        # Get the Excel content
        excel_data = output.getvalue()
        output.close()

        # Generate filename with date range
        filename = f"Service_Execution_Report_{self.date_from or ''}_to_{self.date_to or ''}.xlsx"

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })

        # Return the download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/binary/download_and_delete/{attachment.id}',
            'target': 'self',
        }
    