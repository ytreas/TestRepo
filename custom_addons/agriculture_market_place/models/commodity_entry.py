from odoo import models, fields

class CommodityEntry(models.Model):
    _name = 'commodity.entry' 
    _description = 'Commodity Entry' 
 
    commodity = fields.Char(string='Commodity') 
    unit = fields.Char(string='Unit') 
 
    def action_export_xlsx(self): 
        """Search for the existing commodity Excel file and provide a download link."""
        # Search for the attachment by name 
        attachment = self.env['ir.attachment'].search([('name', '=', 'commodity_entry_sample.xlsx')], limit=1)
         
        if attachment: 
            # If the attachment exists, return it for download 
            return {
                'type': 'ir.actions.act_url',  
                'url': f'/web/content/{attachment.id}?download=true', 
                'target': 'self', 
            } 
        else:
            # If the attachment is not found, display a notification
            return {
                'type': 'ir.actions.client', 
                'tag': 'display_notification',
                'params': {
                    'message': 'File not found!', 
                    'type': 'danger',
                    'sticky': False, 
                } 
            } 
