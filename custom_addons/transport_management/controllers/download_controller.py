from odoo import http
from odoo.http import request
import base64

class DownloadController(http.Controller):
    @http.route('/web/binary/download_and_delete/<int:attachment_id>', type='http', auth="user")
    def download_and_delete(self, attachment_id, **kw):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not attachment.exists():
            return request.not_found()
        
        # Get file data
        file_data = base64.b64decode(attachment.datas)
        
        # Prepare response headers
        headers = [
            ('Content-Type', attachment.mimetype),
            ('Content-Disposition', f'attachment; filename={attachment.name}'),
            ('Content-Length', len(file_data)),
        ]
        
        # Delete the attachment
        attachment.sudo().unlink()
        
        # Return file response
        return request.make_response(file_data, headers)