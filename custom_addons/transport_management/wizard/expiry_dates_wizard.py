from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, date
import nepali_datetime
import io
import base64
import xlsxwriter

# Helper function to convert Gregorian date to Nepali date
def convert_to_bs_date(date_val):
    if date_val:
        nep_date = nepali_datetime.date.from_datetime_date(date_val)
        return nep_date.strftime('%Y-%m-%d')
    return False

class ExpiryDatesWizard(models.TransientModel):
    _name = 'expiry.dates.wizard'
    _description = 'Expiry Dates Wizard'

    date_from = fields.Date("Date From", required=True)
    date_from_bs = fields.Char(string='Date From (BS)', compute='_compute_bs_date', store=True)
    date_to = fields.Date("Date To", required=True)
    date_to_bs = fields.Char(string='Date To (BS)', compute='_compute_bs_date', store=True)
    vehicle_id = fields.Many2one(
                    'vehicle.number',
                    string="Vehicle",
                    domain=[
                        ('available', '=', True),
                        '|',
                            ('heavy', 'in', ['truck', 'mini_truck']),
                            ('vehicle_type.vehicle_type', '=', 'heavy'),
                    ]
                )
    filter_by = fields.Selection([('date', 'Date'), ('vehicle', 'Vehicle')], string="Filter By", required=True, default='date')
    
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
    
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError(_("Date From must be less than or equal to Date To."))

    def _get_report_data(self):
        """Common method to fetch and process report data."""
        self.ensure_one()
        today = date.today()
        domain = []
        print("Initial domain", domain)

        if self.filter_by == 'date':
            date_dom = ['|', '|',
                ('bluebook_expiry_date', '>=', self.date_from),
                ('insurance_expiry_date', '>=', self.date_from),
                ('next_service_due_date', '>=', self.date_from),
            ] + ['|', '|',
                ('bluebook_expiry_date', '<=', self.date_to),
                ('insurance_expiry_date', '<=', self.date_to),
                ('next_service_due_date', '<=', self.date_to),
            ]
            domain = ['&'] + date_dom
        elif self.filter_by == 'vehicle':
            if not self.vehicle_id:
                raise UserError(_("Please select a vehicle."))
            domain = [('id', '=', self.vehicle_id.id)]

        print("Domain", domain)
        vehicle_domain = domain + [
            ('available', '=', True),
            '|',
                ('heavy', 'in', ['truck', 'mini_truck']),
                ('vehicle_type.vehicle_type', '=', 'heavy'),
        ]
        print("Vehicle domain", vehicle_domain)
        vehicles = self.env['vehicle.number'].search(vehicle_domain)
        print("vehicles", vehicles)

        report_data = []
        for v in vehicles:
            try:
                # Safely convert dates
                bluebook_date = False
                insurance_date = False
                service_date = False
                tax_due = False

                if v.bluebook_expiry_date:
                    try:
                        bluebook_date = fields.Date.from_string(v.bluebook_expiry_date)
                        tax_due = bluebook_date + timedelta(days=90)
                        print(f"Bluebook date for vehicle {v.final_number}: {bluebook_date}")
                    except (ValueError, TypeError) as e:
                        print(f"Invalid bluebook date for vehicle {v.final_number}: {e}")

                if v.insurance_expiry_date:
                    try:
                        insurance_date = fields.Date.from_string(v.insurance_expiry_date)
                        print(f"Insurance date for vehicle {v.final_number}: {insurance_date}")
                    except (ValueError, TypeError) as e:
                        print(f"Invalid insurance date for vehicle {v.final_number}: {e}")

                if v.next_service_due_date:
                    try:
                        service_date = fields.Date.from_string(v.next_service_due_date)
                        print(f"Service date for vehicle {v.final_number}: {service_date}")
                    except (ValueError, TypeError) as e:
                        print(f"Invalid service date for vehicle {v.final_number}: {e}")

                # Collect valid dates for remark calculation
                expiries = []
                if bluebook_date:
                    expiries.append(bluebook_date)
                if insurance_date:
                    expiries.append(insurance_date)
                if service_date:
                    expiries.append(service_date)

                # Determine remark based on nearest expiry
                if expiries:
                    nearest = min(expiries)
                    print(f"Nearest expiry date for vehicle {v.final_number}: {nearest}")
                    delta = (nearest - today).days
                    print(f"Days until nearest expiry for vehicle {v.final_number}: {delta}")
                    if delta <= 7:
                        remark = _("Renew within one week")
                    elif delta <= 30:
                        remark = _("Renew within one month")
                    else:
                        remark = _("Expiry date after one month")
                else:
                    remark = _("No expiry dates set")

                print(f"Remark for vehicle {v.final_number}: {remark}")

                # Convert service date to BS
                next_service_due_date_bs = convert_to_bs_date(service_date) if service_date else False

                report_data.append({
                    'vehicle_number': v.final_number,
                    'bluebook_expiry_date': bluebook_date,
                    'insurance_expiry_date': insurance_date,
                    'next_service_due_date': next_service_due_date_bs,
                    'tax_due_date': tax_due,
                    'remarks': remark,
                })
                print(f"Added data for vehicle {v.final_number}")

            except Exception as e:
                print(f"Error processing vehicle {v.final_number}: {str(e)}")
                continue

        if not report_data:
            raise UserError(_("No valid data found for the selected criteria."))

        return report_data

    def print(self):
        """Generate PDF report."""
        report_data = self._get_report_data()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'transport_management.expiry_dates_report_template',
            'report_type': 'qweb-pdf',
            'context': dict(
                self.env.context,
                date_from=self.date_from,
                date_to=self.date_to,
                filter_by=self.filter_by,
                expiry_report_data=report_data
            ),
        }

    def export_to_excel(self):
        """Generate and download Excel report."""
        self.ensure_one()
        report_data = self._get_report_data()

        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Vehicle Expiry Report")

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

        # Set column widths
        worksheet.set_column('A:A', 20)  # Vehicle Number
        worksheet.set_column('B:C', 15)  # Expiry dates
        worksheet.set_column('D:D', 15)  # Service date
        worksheet.set_column('E:E', 15)  # Tax due date
        worksheet.set_column('F:F', 30)  # Remarks

        # Write headers
        headers = [
            "सवारी नं. (Vehicle No.)",
            "ब्लुबुक म्याद (Bluebook Expiry)",
            "बीमा म्याद (Insurance Expiry)",
            "सर्विस मिति (Service Date)",
            "कर तिर्ने मिति (Tax Due)",
            "कैफियत (Remarks)"
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data
        for row, data in enumerate(report_data, start=1):
            worksheet.write(row, 0, data['vehicle_number'], cell_format)
            worksheet.write(row, 1, str(data['bluebook_expiry_date'] or '-'), cell_format)
            worksheet.write(row, 2, str(data['insurance_expiry_date'] or '-'), cell_format)
            worksheet.write(row, 3, str(data['next_service_due_date'] or '-'), cell_format)
            worksheet.write(row, 4, str(data['tax_due_date'] or '-'), cell_format)
            worksheet.write(row, 5, data['remarks'], cell_format)

        workbook.close()
        
        # Get the Excel content
        excel_data = output.getvalue()
        output.close()

        # Generate filename with date range
        filename = f"Vehicle_Expiry_Report_{self.date_from or ''}_to_{self.date_to or ''}.xlsx"

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
