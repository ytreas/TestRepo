#models/transport_pod.py
import os
from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from ..utils.dashboard_notification import notify_transport
import base64
from nepali_datetime import datetime 
import nepali_datetime
import pytz
from datetime import datetime as py_datetime

# Utility function to convert Gregorian date to Nepali BS date
from ..models.transport_order import convert_to_bs_date

class TransportPOD(models.Model):
    _name = 'transport.pod'
    _description = 'Proof of Delivery'
    _order = 'create_date desc'

    # Link to related transport order (Many2one)
    order_id = fields.Many2one(
        'transport.order', string='Order Id', required=True, ondelete='cascade'
    )
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    order_name = fields.Char(
        string='Order Name', related='order_id.customer_name.name', store=True, readonly=True
    )
    # POD (Proof of Delivery) date in Gregorian calendar
    pod_date = fields.Date(
        string='POD Date', default=fields.Date.today, required=True
    )
    estimated_pod_date = fields.Date(related='order_id.scheduled_date_to', 
        string='Estimated POD Date', store=True, readonly=True
    )
    late_type = fields.Selection([
        ('none', 'None'),
        ('weather', 'Weather'),
        ('traffic', 'Traffic'),
        ('address', 'Address Not Found'),
        ('system', 'System Issue'),
        ('other', 'Other'),  
    ],default='none', string='Late Type', help="Reason for late delivery, if applicable")
    remarks = fields.Text(string="Remarks")
    delayed = fields.Boolean(
        string='Delayed', default=False, store=True, compute ='_compute_delayed',
        help="Check this box if the delivery was delayed beyond the estimated date"
    )
    # POD date in Nepali BS format (computed)
    pod_date_bs = fields.Char(string='POD Date BS', compute='_compute_date_bs',store=True)

    # Binary field to store digital signature image
    signature = fields.Binary(string='Digital Signature')

    # File name (with extension) of the uploaded signature image
    signature_file_name = fields.Char(string="Signature File Name")

    # Computed HTML preview of the uploaded signature image
    signature_preview = fields.Html(
        string="Signature Preview", 
        compute="_compute_signature_preview", 
        sanitize=False,
        store=True
    )

    # Additional attachments related to POD
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Attachments'
    )

    # Allowed image file extensions for signature upload
    ALLOWED_SIGNATURE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    request_id = fields.Many2one('customer.request', string='Customer Request',store=True)
    
    
    @api.onchange('pod_date', 'estimated_pod_date')
    def _onchange_late_type_warning(self):
        if (
            self.pod_date and self.estimated_pod_date and
            self.pod_date > self.estimated_pod_date and
            not self.late_type
        ):
            return {
                'warning': {
                    'title': "Late Delivery Warning",
                    'message': "Late Type is recommended because actual delivery date is later than the estimated delivery date.",
                }
            }
    @api.depends('pod_date')
    def _compute_date_bs(self):
        """
        Compute method to convert pod_date to Nepali BS format
        using the utility function from transport_order.
        """
        for record in self:
            record.pod_date_bs = convert_to_bs_date(record.pod_date) if record.pod_date else False

    def _validate_signature_extension(self, file_name):
        """
        Validates that the uploaded signature file has an allowed image extension.
        Raises ValidationError if not.
        """
        if not file_name:
            return
        file_extension = os.path.splitext(file_name)[1][1:].lower()
        if file_extension not in self.ALLOWED_SIGNATURE_EXTENSIONS:
            raise ValidationError(
                "Invalid file type for digital signature! Only PNG, JPG, JPEG, and GIF files are allowed."
            )

    @api.depends('signature')
    def _compute_signature_preview(self):
        """
        Compute method that creates an HTML snippet to preview the signature image.
        Shows a clickable image that links to the full-size version.
        If no image exists, displays a fallback message.
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.signature:
                signature_url = f"{base_url}/web/image?model=transport.pod&id={record.id}&field=signature"
                record.signature_preview = f"""
                    <div style="text-align: left;">
                        <a href="{signature_url}" target="_blank">
                            <img src="{signature_url}" style="max-height: 50px; max-width: 100px; object-fit: contain;"/>
                        </a>
                    </div>
                """
            else:
                record.signature_preview = '<div>No signature available</div>'

    
    def send_notification(self, order_id=None):
        customer_name    = self.order_id.customer_name.name if self.order_id else 'N/A'
        driver_name      = self.order_id.assignment_ids.driver_id.name if self.order_id.assignment_ids.driver_id else 'N/A'
        vehicle_number   = self.order_id.assignment_ids.vehicle_id.final_number if self.order_id.assignment_ids.vehicle_id else 'N/A'
        delivery_address = self.order_id.delivery_location or 'N/A'
        pickup_location  = self.order_id.pickup_location or 'N/A'
        pod_date         = self.pod_date.strftime('%Y-%m-%d') if self.pod_date else 'N/A'
        order_name       = self.order_id.name if self.order_id else self.order_name
        customer_email   = self.order_id.customer_name.email if self.order_id.customer_name and self.order_id.customer_name.email else False
        
        notify_transport(
            env=self.env,
            notification_type='delivery',
            customer_name     = customer_name,
            driver_name       = driver_name,
            order_name        = order_name,
            vehicle_number    = vehicle_number,
            date              = pod_date,
            pickup_location   = pickup_location,
            delivery_location = delivery_address,
            order_id          = order_id
        )
        if customer_email:
            mail_values = {
                'subject': 'Delivery Completed - %s' % order_name,
                'body_html': (
                    f'<p>Dear {customer_name},</p>'
                    f'<p>This is to inform you that your order <strong>{order_name}</strong> has been successfully delivered.</p>'
                    f'<ul>'
                    f'<li><strong>Driver:</strong> {driver_name}</li>'
                    f'<li><strong>Vehicle:</strong> {vehicle_number}</li>'
                    f'<li><strong>Delivery Location:</strong> {delivery_address}</li>'
                    f'<li><strong>Date:</strong> {pod_date}</li>'
                    f'</ul>'
                    f'<p>Thank you for using our service.</p>'
                    f'<p>{self.env.company.name}</p>'
                ),
                'email_to': customer_email,
                'model': self._name,  # Or use self._name
                'res_id': self.id,
            }
            attachment_ids = []
            if self.signature:
                attachment = self.env['ir.attachment'].create({
                    'name': 'Receiver Signature - %s.png' % order_name,
                    'type': 'binary',
                    'datas': self.signature,  # Already base64-encoded
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': 'image/png',
                })
                attachment_ids.append((4, attachment.id))
            if attachment_ids:
                mail_values['attachment_ids'] = attachment_ids

            # report = self.env.ref('your_module.report_pod_template')
            # pdf_content, _ = report._render_qweb_pdf([self.id])

            # attachment = self.env['ir.attachment'].create({
            #     'name': 'POD - %s.pdf' % self.order_id.name,
            #     'type': 'binary',
            #     'datas': base64.b64encode(pdf_content),
            #     'res_model': self._name,
            #     'res_id': self.id,
            #     'mimetype': 'application/pdf',
            # })
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

        
    @api.model
    def create(self, vals):
        kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        now_nep = py_datetime.now(kathmandu_tz)
        now_nep = now_nep.replace(microsecond=0)

        """
        Overrides create method to:
        - Validate file extension for uploaded signature
        - Recompute signature preview after creation
        """
        if 'signature_file_name' in vals:
            self._validate_signature_extension(vals.get("signature_file_name"))
            
        record = super(TransportPOD,self).create(vals)
        # if (record.pod_date > record.estimated_pod_date):
        #     record.delayed = 'True'
        if record.order_id:
            today_date = fields.Date.today()
            record.order_id.state = 'delivered'
            record.order_id.update_time =  now_nep.strftime("%H:%M:%S")
            # record.order_id.update_date_bs = convert_to_bs_date(today_date)
            record.order_id.actual_delivery_date = record.pod_date
            # record.order_id.request_id.state = 'delivered'
            record.order_id.request_line_id.state = 'delivered'
            record.order_id.request_id.delivery_details_id = [(6,0,record.id)]
            result = self.env['duty.allocation'].search([('transport_order','=',record.order_id.name)],limit=1)
            if result:
                result.state = 'delivered'
                
            record.send_notification(order_id=record.order_id.id)
            
        if 'signature' in vals or 'signature_file_name' in vals:
            record._compute_signature_preview()
        return record

    def write(self, vals):
        kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        now_nep = py_datetime.now(kathmandu_tz)
        now_nep = now_nep.replace(microsecond=0)
        
        # nep_date = datetime.now()
        if 'signature_file_name' in vals:
            self._validate_signature_extension(vals.get("signature_file_name"))
            
        res = super().write(vals)
        if 'signature' in vals or 'signature_file_name' in vals:
            self._compute_signature_preview()
        for record in self:
            if record.pod_date:
                # today_date = fields.Date.today()
                # record.order_id.update_date_bs = convert_to_bs_date(today_date)
                record.order_id.update_time =  now_nep.strftime("%H:%M:%S")
                record.order_id.actual_delivery_date = record.pod_date
        return res
    
    @api.depends('pod_date', 'estimated_pod_date')
    def _compute_delayed(self):
        for rec in self:
            rec.delayed = (
                rec.pod_date and rec.estimated_pod_date and rec.pod_date > rec.estimated_pod_date
        )
