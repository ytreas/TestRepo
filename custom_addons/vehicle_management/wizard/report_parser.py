from odoo import models, api

class FuelConsumptionReport(models.AbstractModel):
    _name = 'report.vehicle_management.fuel_consumption_report_template'
    _description = 'Fuel Consumption Report'

    def format_number_with_commas(self, amount):
        """Format a number with commas and include decimals."""
        if amount is None:
            return "0"
        try:
            # Convert the number to a string and split into integer and decimal parts
            amount_str = f"{amount:.2f}"  # Ensure the number has two decimal places
            if "." in amount_str:
                integer_part, decimal_part = amount_str.split(".")
            else:
                integer_part, decimal_part = amount_str, None

            # Format the integer part using the Indian numbering system
            if len(integer_part) > 3:
                last_three = integer_part[-3:]
                rest = integer_part[:-3]
                rest_with_commas = ",".join([rest[max(i - 2, 0):i] for i in range(len(rest), 0, -2)][::-1])
                formatted_integer = f"{rest_with_commas},{last_three}"
            else:
                formatted_integer = integer_part

            # Combine the formatted integer part with the decimal part
            if decimal_part:
                return f"{formatted_integer}.{decimal_part}"
            return formatted_integer
        except Exception:
            return str(amount)

    @api.model
    def _get_report_values(self, docids, data=None):
        if data is None:
            data = {}
        
        return {
            'doc_ids': docids,
            'doc_model': 'fuel.entry',
            'docs': self.env['fuel.entry'].browse(docids),
            'data': data,
            'format_number_with_commas': self.format_number_with_commas,
        }