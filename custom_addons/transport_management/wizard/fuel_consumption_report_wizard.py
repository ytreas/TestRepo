from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import io
import base64
import xlsxwriter
from ..models.transport_order import convert_to_bs_date

class FuelConsumptionReportWizard(models.TransientModel):
    _name = 'fuel.consumption.report.wizard'
    _description = 'Fuel Consumption Report Wizard'

    FILTERS = [
        ('date', 'Date Range'),
        ('vehicle', 'Vehicle'),
        ('fuel_type', 'Fuel Type'),
    ]
    filter_by    = fields.Selection(FILTERS, string="Filter By", required=True, default='date')
    date_from    = fields.Date(string="From Date")
    date_to      = fields.Date(string="To Date")
    date_from_bs = fields.Char(string="From Date (BS)", compute='_compute_bs_date')
    date_to_bs   = fields.Char(string="To Date (BS)", compute='_compute_bs_date')
    vehicle_id   = fields.Many2one('vehicle.number', string="Vehicle",
                                   domain=[
                                        ('available', '=', True),
                                        '|',
                                            ('heavy', 'in', ['truck', 'mini_truck']),
                                            ('vehicle_type.vehicle_type', '=', 'heavy'),
                                    ])
    fuel_type_id = fields.Many2one('fuel.types', string="Fuel Type")

    @api.constrains('date_from', 'date_to')
    def _compute_bs_date(self):
        for rec in self:
            rec.date_from_bs = convert_to_bs_date(rec.date_from) if rec.date_from else ''
            rec.date_to_bs = convert_to_bs_date(rec.date_to) if rec.date_to else ''

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

    def _get_report_data(self):
        """Helper method to fetch and process report data."""
        self.ensure_one()
        print("Wizard Filter:", self.filter_by)

        # Build domain
        domain = []
        if self.filter_by == 'date':
            if not (self.date_from and self.date_to):
                raise UserError(_("Please set both From Date and To Date."))
            domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        elif self.filter_by == 'vehicle':
            if not self.vehicle_id:
                raise UserError(_("Please select a Vehicle."))
            domain = [('vehicle_id', '=', self.vehicle_id.id)]
        elif self.filter_by == 'fuel_type':
            if not self.fuel_type_id:
                raise UserError(_("Please select a Fuel Type."))
            domain = [('fuel_type_id', '=', self.fuel_type_id.id)]

        print("Constructed domain:", domain)
        
        extra_domain = [
            ('vehicle_id.available', '=', True),
            '|',
            ('vehicle_id.heavy', 'in', ['truck', 'mini_truck']),
            ('vehicle_id.vehicle_type.vehicle_type', '=', 'heavy'),
        ]
        print("Extra domain:", extra_domain)
        full_domain = domain + extra_domain
        print("Full domain:", full_domain)
        
        entries = self.env['fuel.entry'].search(full_domain, order='date, current_odometer')
        print(f"Total entries found: {len(entries)}")

        report_data = []
        # Group by date and vehicle
        grouped = {}
        for e in entries:
            key = (e.date, e.vehicle_id.id)
            grouped.setdefault(key, []).append(e)

        for (day, veh_id), day_entries in grouped.items():
            print(f"Processing entries for date {day} and vehicle {veh_id}")
            
            if len(day_entries) > 1:
                # Multiple entries for the day
                opening = day_entries[0].current_odometer
                closing = day_entries[-1].current_odometer
                print(f"Multiple entries found. Opening: {opening}, Closing: {closing}")
            else:
                # Single entry for the day - need to find previous reading
                current_entry = day_entries[0]
                closing = current_entry.current_odometer
                
                # Search for the most recent previous entry for this vehicle
                previous_entry = self.env['fuel.entry'].search([
                    ('vehicle_id', '=', veh_id),
                    ('date', '<', day),
                    ('current_odometer', '<', closing)
                ], order='date desc, current_odometer desc', limit=1)

                if previous_entry:
                    opening = previous_entry.current_odometer
                    print(f"Found previous entry for vehicle {current_entry.vehicle_id.final_number} "
                        f"on {previous_entry.date} with odometer {opening}")
                else:
                    opening = closing
                    print(f"No previous entry found for vehicle {current_entry.vehicle_id.final_number}. "
                        f"Using closing value {closing} as opening.")

            # Calculate distance
            dist = closing - opening if closing > opening else 0
            print(f"Calculated distance: {dist} km")

            # Calculate total fuel and mileage
            total_fuel = sum(e.quantity for e in day_entries if not e.is_electric)
            print(f"Total fuel consumed: {total_fuel} liters")
            
            # Calculate mileage only if we have both distance and fuel
            mileage = (dist / total_fuel) if total_fuel and dist > 0 else 0.0
            print(f"Calculated mileage: {mileage} km/l")

            # Get remarks
            remarks = day_entries[-1].remarks or _('Normal')

            # Convert date to BS
            day_bs = convert_to_bs_date(day) if day else ''

            # Prepare report data
            entry_data = {
                'date': day_bs,
                'truck_no': day_entries[0].vehicle_id.final_number,
                'opening_km': opening,
                'closing_km': closing,
                'distance': dist,
                'fuel_type': day_entries[0].fuel_type_id.name,
                'fuel_filled': total_fuel,
                'mileage': round(mileage, 2),
                'remarks': remarks,
            }
            report_data.append(entry_data)
            print("Added report data:", entry_data)

        if not report_data:
            print("No data found for the selected criteria")
            raise UserError(_("No records found for the selected criteria."))

        return report_data
    
    def print_report(self):
        """Generate PDF report."""
        report_data = self._get_report_data()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'transport_management.fuel_consumption_report_template',
            'report_type': 'qweb-pdf',
            'context': dict(self.env.context,
                date_from=self.date_from_bs,
                date_to=self.date_to_bs,
                fuel_report_data=report_data),
        }

    def export_to_excel(self):
        """Generate and download Excel report."""
        self.ensure_one()
        report_data = self._get_report_data()

        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Fuel Consumption Report")

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
        worksheet.set_column('A:A', 15)  # Date
        worksheet.set_column('B:B', 20)  # Truck No
        worksheet.set_column('C:D', 15)  # Opening/Closing KM
        worksheet.set_column('E:E', 12)  # Distance
        worksheet.set_column('F:F', 20)  # Fuel Type
        worksheet.set_column('G:G', 15)  # Fuel Filled
        worksheet.set_column('H:H', 15)  # Mileage
        worksheet.set_column('I:I', 25)  # Remarks

        # Write headers
        headers = [
            "मिति (Date)", "ट्रक नं. (Truck No.)", "सुरु किमी (Opening KM)",
            "अन्त्य किमी (Closing KM)", "दूरी (Distance in km)",
            "ईन्धनको किसिम (Fuel Type)", "ईन्धन भरेको मात्र (Fuel Filled in Litres)",
            "औसत माइलेज (KM/Litre)", "कैफियत (Remarks)"
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data
        for row, data in enumerate(report_data, start=1):
            worksheet.write(row, 0, data['date'], cell_format)
            worksheet.write(row, 1, data['truck_no'], cell_format)
            worksheet.write(row, 2, data['opening_km'], cell_format)
            worksheet.write(row, 3, data['closing_km'], cell_format)
            worksheet.write(row, 4, data['distance'], cell_format)
            worksheet.write(row, 5, data['fuel_type'], cell_format)
            worksheet.write(row, 6, data['fuel_filled'], cell_format)
            worksheet.write(row, 7, data['mileage'], cell_format)
            worksheet.write(row, 8, data['remarks'], cell_format)

        workbook.close()
        
        # Get the Excel content
        excel_data = output.getvalue()
        output.close()

        # Generate filename with date range
        filename = f"Fuel_Consumption_Report_{self.date_from or ''}_to_{self.date_to or ''}.xlsx"

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