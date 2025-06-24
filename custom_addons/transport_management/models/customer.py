from odoo import models, fields, api, _
from ..models.transport_order import convert_to_bs_date
from odoo.exceptions import UserError ,ValidationError
from ..utils.dashboard_notification import notify_transport
from datetime import timedelta ,datetime
from ..models.mailsender import MailSender
import pytz

class CustomerRequest(models.Model):
    _name = "customer.request"
    _description = "Customer Request"
    _order = "create_date desc"
    _rec_name = 'code'

    code = fields.Char(
        string='Request Reference',
        required=True,
        readonly=True,
        default=lambda self: _('New')
    )
    order_type = fields.Selection([
        ('single_order', 'Single Order'),
        ('multiple_order', 'Multiple Order')
    ], string='Order Type', default='single_order')

    address = fields.Char(string="Address")
    order_date = fields.Date(string="Order Date", required= True)
    
    order_date_bs = fields.Char(string="Order Date BS", store =True, _compute = '_compute_date_bs')
    
    estimated_pickup_date = fields.Date(string="Estimated Pickup Date", required=True)
    estimated_delivery_date = fields.Date(string="Estimated Delivery Date", required=True)
    estimated_pickup_date_bs = fields.Char(string="Estimated Pickup Date(BS)",_compute = '_compute_date_bs' ,store=True)
    estimated_delivery_date_bs = fields.Char(string="Estimated Delivery Date(BS)",_compute = '_compute_date_bs' ,store=True)
    
    pickup_date = fields.Date(string="Acutal Pickup Date")
    pickup_date_bs = fields.Char(string="Estimated Pickup Date(BS)", _compute = '_compute_date_bs' ,store=True)
    delivery_date = fields.Date(string="Acutal Delivery Date",)
    delivery_date_bs = fields.Char(string="Actual Delivery Date(BS)",_compute = '_compute_date_bs' ,store=True)
    # The code snippet you provided is not complete and lacks context. It appears to be a comment in a
    # Python script that mentions "request_details". Without the actual code or more information, it
    # is not possible to determine what the code is doing. If you provide more context or the complete
    # code, I can help you understand its functionality.
    request_details = fields.One2many(
        "customer.request.line", "line_id", string="Request Line"
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("accept", "Accepted"),
            ("complete","Completed"),
        ],
        string="Status",
        default="draft",
    )
    total_weight = fields.Float(string="Total Weight", compute="_compute_total_weight",store=True)
    # total_price = fields.Float(string="Total Price" , compute = "_compute_total_price",store=True)
    auto_place_order = fields.Boolean(string="Auto Select Vehicle", default=False)
    select_vehicle = fields.Many2one("vehicle.number", string="Select Vehicle",
                                     domain=[
                                        ('available', '=', True),
                                        '|',
                                            ('heavy', 'in', ['truck', 'mini_truck']),
                                            ('vehicle_type.vehicle_type', '=', 'heavy'),
                                    ])
  
    weight_for_vehicle = fields.Float(string="Weight for Vehicle", compute="_compute_weight_for_vehicle", store=True)

    delivery_details_id = fields.One2many('transport.pod', 'request_id', string='Delivery Details')
    
    feedback = fields.Text(string="Write Feedback")

    def _compute_manual_request_name(self):
        """
        Helper method to compute a manual order name in the pattern "Request/XXXXX".
        It searches for the most recently created request, extracts the numerical
        part from the request name (expected in the format Request/XXXXX), increments it,
        and returns a new name with the number padded to five digits.
        """
        # Retrieve the most recent request based on the highest id
        last_request = self.search([], order="id desc", limit=1)
        if last_request and last_request.code:
            try:
                # Attempt to extract the numerical part from the request code
                last_number = int(last_request.code.split('/')[-1])
            except Exception:
                # If extraction fails, start numbering from 0
                last_number = 0
        else:
            # No previous request found
            last_number = 0
        # Increment the number and pad with zeros to have five digits
        new_number = last_number + 1
        return "Request/" + str(new_number).zfill(5)
    
    @api.model
    def create(self, vals):
        # Compute a manual request code if the default is still "New"
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self._compute_manual_request_name()
        # Create the customer request record first.
        request = super(CustomerRequest, self).create(vals)
        return request
    
    def send_feedback(self):
        result = self.env['transport.order'].search([('request_id','=',self.id)])
        if result:
            result.feedback = self.feedback

    def sendNotification(self, order_id=None, customer_name=None, source=None, destination=None):
        customer_name    = customer_name
        pickup_location  = source
        delivery_location= destination
        date             = self.order_date

        notify_transport(
            env=self.env,
            notification_type='order',
            customer_name=customer_name,
            pickup_location=pickup_location,
            delivery_location=delivery_location,
            date=date, 
            order_id=order_id,
        )
        # notifier = OrderNotifier(
        #     self.env,
        #     customer_name,
        #     pickup_location,
        #     delivery_location,
        #     date,
        #     order_id=order_id
        # )
        # notifier.notify()

    @api.depends('order_date','pickup_date','delivery_date', 'estimated_pickup_date', 'estimated_delivery_date')
    def _compute_date_bs(self):
        for record in self:

            record.order_date_bs = convert_to_bs_date(record.order_date) if record.order_date else False
            record.pickup_date_bs = convert_to_bs_date(record.pickup_date) if record.pickup_date else False
            record.delivery_date_bs = convert_to_bs_date(record.delivery_date) if record.delivery_date else False
            record.estimated_pickup_date_bs = convert_to_bs_date(record.estimated_pickup_date) if record.estimated_pickup_date else False
            record.estimated_delivery_date_bs = convert_to_bs_date(record.estimated_delivery_date) if record.estimated_delivery_date else False

    @api.depends("total_weight")
    def _compute_weight_for_vehicle(self):
        for rec in self:
            if rec.total_weight > 0 and not rec.auto_place_order:
                rec.weight_for_vehicle = rec.total_weight
            else:
                rec.weight_for_vehicle = 0.0
    @api.depends("request_details.weight")
    def _compute_total_weight(self):
        for record in self:
            total_weight = sum(record.request_details.mapped("weight"))
            record.total_weight = total_weight
    # @api.depends("request_details.total_price")
    # def _compute_total_price(self):
    #     for record in self:
    #         total_price = sum(record.request_details.mapped("total_price"))
    #         record.total_price = total_price     

    def _send_order_confirmation_email(self, record):
        """Send order confirmation email to trader"""
        print("Sending email to:", record.trader_name.email)
        if record.trader_name.email:
            try:
                mail_sender = MailSender(self.env)
                body_html = f'''
                    <p>Dear {record.trader_name.name},</p>
                    <p>Your order has been placed successfully.</p>
                    <p>Pickup Location: {record.source_location}</p>
                    <p>Delivery Location: {record.destination_location}</p>
                    <p>Thank you for choosing us!</p>
                '''
                
                mail_sender.send_mail(
                    email_to=record.trader_name.email,
                    subject='Order Confirmation',
                    body_html=body_html,
                    model='customer.request',
                    res_id=self.id
                )
                print("Email sent successfully to:", record.trader_name.email)
            except Exception as e:
                print(f"Error sending email: {e}")
        else:
            print("Email sending skipped: Email address is not available for the customer.")
            raise UserError("Email address is not available for the customer.")
    
    def _send_sms_notification(self, phone_number, message):
        """Send SMS notification to a phone number"""
        print("Sending SMS to:", phone_number)
        if phone_number:
            try:
                sms_service = self.env['sparrow.sms']
                result = sms_service.send_sms(message, phone_number)
                
                if result:
                    print(f"SMS sent successfully to {phone_number}")
                else:
                    print(f"Failed to send SMS to {phone_number}")
                    
            except Exception as e:
                print(f"Error sending SMS: {e}")
                
        else:
            print("Phone number is not available. Skipping SMS.")
    
    def action_confirm(self):
        # 1) Validate every detail line
        for detail in self.request_details:
            if detail.weight <= 0:
                raise UserError("Weight must be greater than 0.")
            if not detail.items:
                raise UserError("Items must be selected.")

        # 2) Create a single order
        for rec in self:
            for record in rec.request_details:
                if self.auto_place_order:
                    print("Inside auto place order",self.auto_place_order)
                    # vehicle = self.env["vehicle.number"].search([("state", "=", "available") and ("volume","=",self.total_weight)], limit=1)
                    order = self.env["transport.order"].create({
                        "request_id":self.id,
                        "request_line_id":record.id,
                        "customer_name": record.trader_name.id,
                        "receiver_name" :record.receiver_name.id,
                        "pickup_location":  record.source if record.source else record.sender_tole,
                        "delivery_location":  record.destination if record.destination else record.receiver_tole,
                        "pickup_address": record.source_location,
                        # "pickup_address":f"{self.source_province.name},{self.source_palika.palika_name}, {self.source_district.district_name}, {self.source_ward}" if self.source else self.request_details.items.destination_location,
                        "delivery_address": record.destination_location,
                        # "preferred_truck_id": vehicle.id if vehicle else False,
                        # 'assignment_ids': [(0, 0, {'vehicle_id': vehicle.id})] if vehicle else False,
                        "request_details_ids": [(6, 0, record.items.ids)],
                        "cargo_weight": record.weight,
                        # "total_valuation":record.total_price,
                        "scheduled_date_from":self.estimated_pickup_date,
                        "scheduled_date_to":self.estimated_delivery_date,
                        "state": "draft",  
                    })
                    if order:
                        self.sendNotification(order_id=order.id, customer_name=record.trader_name.name, source=record.source, destination=record.destination)

                        # Send SMS
                        message = f"Dear {record.trader_name.name}, your order has been placed successfully. Pickup Location: {record.source_location}, Delivery Location: {record.destination_location}. Thank you for choosing us!"
                        print("Message to send:", message)
                        print("Phone number to send SMS:", record.trader_name.phone)
                        self._send_sms_notification(record.trader_name.phone, message)

                        # Send email using the new method
                        self._send_order_confirmation_email(record)

                    else:
                        raise UserError("No available vehicles found.")
                    
                else:
                    ktm_tz = pytz.timezone("Asia/Kathmandu")
                    ktm_now = datetime.now(ktm_tz)
                    ktm_naive = ktm_now.replace(tzinfo=None)

                    ktm_date = ktm_naive.date()
                    ktm_time = ktm_naive.time()
                    nepali_date = convert_to_bs_date(ktm_date)
                    print("Inside else auto place order",self.auto_place_order,record.trader_name.name,record.id,self.id, rec.request_details.ids)
                    order = self.env["transport.order"].create({
                        "request_id":self.id,
                        "request_line_id":record.id,
                        "customer_name": record.trader_name.id,
                        "receiver_name" :record.receiver_name.id,
                        "pickup_location":  record.source if record.source else record.sender_tole,
                        "delivery_location":  record.destination if record.destination else record.receiver_tole,
                        "pickup_address": record.source_location,
                        "delivery_address": record.destination_location,
                        "preferred_truck_id": self.select_vehicle.id,
                        'assignment_ids': [(0, 0, {'vehicle_id': self.select_vehicle.id})] if self.select_vehicle else False,
                        "request_details_ids": [(6, 0, record.items.ids)],
                        "cargo_weight": record.weight,
                        # "total_valuation":record.total_price,
                        "scheduled_date_from":self.estimated_pickup_date,
                        "scheduled_date_to":self.estimated_delivery_date,
                        "update_date_bs":nepali_date,
                        "update_time":ktm_time,
                        "state": "draft",
                        
                    }) 
                    if order:
                        self.sendNotification(order_id=order.id, customer_name=record.trader_name.name, source=record.source, destination=record.destination)

                        # Send SMS
                        message = f"Dear {record.trader_name.name}, your order has been placed successfully. Pickup Location: {record.source_location}, Delivery Location: {record.destination_location}. Thank you for choosing us!"
                        print("Message to send:", message)
                        print("Phone number to send SMS:", record.trader_name.phone)
                        self._send_sms_notification(record.trader_name.phone, message)

                        # Send email using the new method
                        self._send_order_confirmation_email(record)

                    else:
                        raise UserError("No available vehicles found.")
        
        self.state = "confirmed"
        self.request_details.state = "confirmed"
        return {
            "effect": {
                "fadeout": "slow",
                "message": _("Order placed Successfully"),
                "type": "rainbow_man",
            }
        } 
        

    def action_complete(self):
        self.state = "complete"
    # def action_cancel(self):
    #     self.state = "cancel"
class RequestLine(models.Model):
    _name = 'customer.request.line'
    _description = 'Customer Request Line'
    
    trader_name = fields.Many2one("amp.trader",string="Sender Name", required=True)
    receiver_name = fields.Many2one("amp.trader",string="Receiver Name", required=True)
    line_id = fields.Many2one("customer.request", string="Request ID")
    items = fields.One2many("customer.request.details","request_id", string="Items", required=True)
    weight = fields.Float(string='Total Weight(kg)', digits=(12, 3), compute='_compute_total_weight', store=True)
    # total_price = fields.Float(string='Total Price', compute='_compute_total_price', store=True)
    description = fields.Text(string="Description")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("advance","Advance Payment Done"),
            ("accept", "Process"),
            ('in_transit', 'In Transit'),
            ("delivered", "Delivered"),
            ("complete","Completed"),
            ("cancelled","Cancelled")
        ],
        string="Status",
        default="draft",
    )
    cancel_reason = fields.Text(string="Remarks")
    paid = fields.Boolean(string="Paid", default=False)
    total_charge = fields.Float(string="Total Charge Without Tax",store=True)
    advance_amount = fields.Float(string="Advance Amount",store=True)
    invoice_id = fields.Many2one('account.move', "Advance Invoice")
    payment_id = fields.Many2one('account.payment', "Payment")
    # final_invoice_id = fields.Many2one('account.move', "Final Invoice")
    tax_id = fields.Many2one('account.tax',string="Tax" ,readonly=True)
    total_charge_with_tax = fields.Float(string="Total Charge with Tax",store=True,readonly=True)
    payment_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("advance", " Advance Paid"),
            ("full", "Full Paid"),
        ],
        string="Payment Status",
        default="draft",
    )
    
    destination = fields.Char(string="Destination")
    destination_province = fields.Many2one('location.province',string="Province")
    destination_district = fields.Many2one('location.district',string="District",   domain="[('province_name', '=', destination_province)]" )
    destination_palika = fields.Many2one('location.palika', string="Palika", domain="[('district_name', '=', destination_district)]")
    destination_ward = fields.Char(string="Ward No:")
    
    source = fields.Char(string="Source")
    source_province = fields.Many2one('location.province',string="Province")
    source_district = fields.Many2one('location.district',string="District",   domain="[('province_name', '=', source_province)]" )
    source_palika = fields.Many2one('location.palika', string="Palika", domain="[('district_name', '=', source_district)]")
    source_ward = fields.Char(string="Ward No:")
    
    source_location = fields.Text(string="Source Location", compute='_compute_location_info', store=True)
    destination_location = fields.Text(string="Destination Location", compute='_compute_location_info', store=True)
    

    same_as_sender = fields.Boolean(string="Same as Sender Location:" ,default=False)
    same_as_receiver = fields.Boolean(string="Same as Receiver Location", default=False)
    receiver_tole = fields.Char(string="Receiver Tole", related = 'receiver_name.trader_tole_name' ,store=True)
    receiver_province = fields.Many2one('location.province',related='receiver_name.trader_province',string="Province" ,store=True)
    receiver_district = fields.Many2one('location.district',related='receiver_name.trader_district',string="District",  store=True) 
    receiver_palika = fields.Many2one('location.palika',related='receiver_name.trader_palika', string="Palika", store=True)
    receiver_ward = fields.Char(string="Ward No:",related='receiver_name.trader_ward',store=True)
    
    sender_tole = fields.Char(string="Sender Tole", related='trader_name.trader_tole_name', store=True)
    sender_province = fields.Many2one('location.province',related='trader_name.trader_province',string="Province",store=True)
    sender_district = fields.Many2one('location.district',related='trader_name.trader_district',string="District",  store=True)
    sender_palika = fields.Many2one('location.palika',related='trader_name.trader_palika', string="Palika", store=True)
    sender_ward = fields.Char(string="Ward No:",related='trader_name.trader_ward',store=True)
    

    def action_make_advance_payment(self):
        print("Advance inovice id:",self.invoice_id.id)
        if self.advance_amount <= 0:
            raise UserError("Advance amount must be greater than 0.")
        partner = self.env['res.partner'].search([('name', '=', self.trader_name.name)], limit=1)
        if not partner:
            raise UserError("Customer not found.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Final Invoice',
            'res_model': 'invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_date': fields.Date.today(),  # Default today's date
                'default_customer': partner.id, 
                'default_total_amount':self.total_charge,# Assuming 'partner_id' is the customer field
                'default_amount': self.advance_amount, 
                'default_invoice_id':self.invoice_id.id,
                'default_payment_id':self.payment_id.id,
                'default_tax_id':self.tax_id.id,  
                # 'default_advance_invoice_id':self.advance_invoice_id.id,
                'default_invoice_type':'advance',
                'default_request_line_id':self.id,# Assuming 'amount_due' is the amount to be passed
            }
        }
        
        # for record in self:
        #     if not record.advance_amount:
        #         raise UserError("Please set an advance amount.")

        #     partner = self.env['res.partner'].search([('name', '=', record.customer_name.name)], limit=1)

        #     invoice_vals = {
        #         'move_type': 'out_invoice',
        #         'partner_id': partner.id,
        #         'invoice_date': fields.Date.today(),
        #         'invoice_date_due': fields.Date.today() + timedelta(days=7),
        #         'invoice_line_ids': [
        #             (0, 0, {
        #                 'name': "Advance Payment for Transport",
        #                 'quantity': 1.0,
        #                 'price_unit': record.advance_amount,
        #                 'account_id': 360,  # Revenue account
        #             }),
        #         ],
        #     }

        #     advance_invoice = self.env['account.move'].create(invoice_vals)
        #     record.advance_invoice_id = advance_invoice.id
        #     return {
        #         'name': 'Advance Invoice',
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'account.move',
        #         'res_id': advance_invoice.id,
        #         'view_mode': 'form',
        #     }

    
    def action_make_final_invoice(self):
        print("Advance inovice id:",self.invoice_id)
        if self.advance_amount <= 0:
            raise UserError("Advance amount must be greater than 0.")
        partner = self.env['res.partner'].search([('name', '=', self.trader_name.name)], limit=1)
        if not partner:
            raise UserError("Customer not found.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Final Invoice',
            'res_model': 'invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
             'context': {
                'default_invoice_date': fields.Date.today(),  # Default today's date
                'default_customer': partner.id, 
                'default_total_amount':self.total_charge,
                'default_tax_amount':self.total_charge_with_tax - self.total_charge,# Assuming 'partner_id' is the customer field
                'default_amount': self.advance_amount, 
                'default_invoice_id':self.invoice_id.id,
                'default_payment_id':self.payment_id.id,
                'default_tax_id':self.tax_id.id,  
                # 'default_advance_invoice_id':self.advance_invoice_id.id,
                'default_invoice_type':'final',
                'default_request_line_id':self.id,# Assuming 'amount_due' is the amount to be passed
            }
        }

    @api.onchange('source_province', 'source_district',
                 'source_palika', 'source_ward',
                 'destination', 'destination_province',
                 'destination_district', 'destination_palika',
                 'destination_ward','sender_province',
                 'sender_district','sender_palika','sender_ward',
                 'receiver_province',
                 'receiver_district','receiver_palika','receiver_ward')
    @api.depends('source_province', 'source_district',
                 'source_palika', 'source_ward',
                 'destination', 'destination_province',
                 'destination_district', 'destination_palika',
                 'destination_ward','sender_province',
                 'sender_district','sender_palika','sender_ward',
                 'receiver_province',
                 'receiver_district','receiver_palika','receiver_ward')
    def _compute_location_info(self):
        for record in self:
            # Source Location
            province = record.source_province.name if record.source_province else (record.sender_province.name if record.sender_province else '')
            district = record.source_district.district_name if record.source_district else (record.sender_district.district_name if record.sender_district else '')
            palika = record.source_palika.palika_name if record.source_palika else (record.sender_palika.palika_name if record.sender_palika else '')
            ward = f"Ward {record.source_ward}" if record.source_ward else (f"Ward {record.sender_ward}" if record.sender_ward else '')

            source_location = ", ".join(filter(None, [province, district, palika, ward]))
         
            record.source_location = source_location
            # Destination Location
            province = record.destination_province.name if record.destination_province else (record.receiver_province.name if record.receiver_province else '')
            district = record.destination_district.district_name if record.destination_district else (record.receiver_district.district_name if record.receiver_district else '')
            palika = record.destination_palika.palika_name if record.destination_palika else (record.receiver_palika.palika_name if record.receiver_palika else '')
            ward = f"Ward {record.destination_ward}" if record.destination_ward else (f"Ward {record.receiver_ward}" if record.receiver_ward else '')
            destination_location = ", ".join(filter(None, [province, district, palika, ward]))
            record.destination_location = destination_location
            
    @api.depends("items.weight")
    def _compute_total_weight(self):
        for record in self:
            total_weight = sum(record.items.mapped("weight"))
            record.weight = total_weight
    # @api.depends("items.taxed_total_price")
    # @api.onchange("items.taxed_total_price")
    # def _compute_total_price(self):
    #     for record in self:
    #         record.total_price = sum(record.items.mapped("taxed_total_price"))
            

    def action_view_invoice(self):
        pass
        # result = self.env["account.move"].search([("partner_id", "=", self.invoice_id.id)], order="id desc", limit=1)
        # if result:
        #     return {
        #         "name": _("Invoice"),
        #         "view_mode": "form",
        #         "res_model": "account.move",
        #         "res_id": result.id,
        #         "type": "ir.actions.act_window",
        #     }
        # else:
        #     raise UserError(_("No invoice "))
    def action_view_final_invoice(self):
        pass
        # result = self.env["account.move"].search([("id", "=", self.invoice_id.id)], order="id desc", limit=1)
        # if result:
        #     return {
        #         "name": _("Invoice"),
        #         "view_mode": "form",
        #         "res_model": "account.move",
        #         "res_id": result.id,
        #         "type": "ir.actions.act_window",
        #     }
        # else:
        #     raise UserError(_("No invoice"))
        
    # @api.constrains('destination','source','sender_tole','receiver_tole',
    #                 'source_province','destination_province','sender_province','receiver_province')
    # def _check_either_destination_or_receiver(self):
    #     for record in self:
    #         if not (record.destination and record.receiver_tole):
    #             raise ValidationError("You must fill Destination Address")
    #         if not (record.source and record.sender_tole):
    #             raise ValidationError("You must fill Source Address")
    #         if not (record.source_province or record.sender_province):
    #             raise ValidationError("You must fill Source Province")
    #         if not (record.destination_province or record.receiver_province):
    #             raise ValidationError("You must fill Destination Province")
# class requestLocation(models.Model):
#     _name = 'request.location'
#     _description = 'Request Location'
#     _rec_name = 'name'
#     # location_id = fields.Many2one("customer.request.details", string="Request Details ID")
#     destination = fields.Char(string="Destination", required=True)
#     destination_province = fields.Many2one('location.province',required=True,string="Province")
#     destination_district = fields.Many2one('location.district',required=True,string="District",   domain="[('province_name', '=', destination_province)]" )
#     destination_palika = fields.Many2one('location.palika', string="Palika", domain="[('district_name', '=', destination_district)]")
#     destination_ward = fields.Char(string="Ward No:")
    
#     source = fields.Char(string="Source", required=True)
#     source_province = fields.Many2one('location.province',required=True,string="Province")
#     source_district = fields.Many2one('location.district',required=True,string="District",   domain="[('province_name', '=', source_province)]" )
#     source_palika = fields.Many2one('location.palika', string="Palika", domain="[('district_name', '=', source_district)]")
#     source_ward = fields.Char(string="Ward No:")
#     name = fields.Char(string="Location Name", compute="_compute_name", store=True)
    
#     @api.depends('source', 'destination')
#     def _compute_name(self):
#         for rec in self:
#             if rec.source and rec.destination:
#                 rec.name = f"{rec.source} ➜ {rec.destination}"
#             else:
#                 rec.name = "Location selected"
  
class CustomerRequestDetails(models.Model):
    _name = "customer.request.details"
    _description = "Customer Request Details"
    
    request_id = fields.Many2one("customer.request.line", string="Request ID")
    # location = fields.Many2one("request.location", string="Location")

    transport_id = fields.Many2one("transport.order", string="Transport Order")
    
    items = fields.Many2one("amp.commodity.master", string="Items", required=True)
    weight = fields.Float(string='Total Weight(kg)', digits=(12, 3), compute='_compute_total', store=True)
    quantity = fields.Float(string="Quantity", required=True)
    
    # per_unit_price = fields.Float(string="Unit Price(Rs)")
    unit = fields.Many2one('uom.uom', string='Standard Unit',related = 'items.unit' , store=True)
    description = fields.Text(string="Description")
    converter = fields.Many2one('uom.uom', string='Convertor', default=lambda self: self.env.ref('uom.product_uom_kgm'))
    
    # tax = fields.Many2one('account.tax',string="Tax")
    # untaxed_total_price = fields.Float(string="Untaxed Amount(Rs)", compute="_compute_untaxed_total_price", store=True)
    # taxed_total_price = fields.Float(string="Total Price(Rs)", compute="_compute_total_price", store=True)
    
    # source_location = fields.Text(string="Source Location", compute='_compute_location_info', store=True)
    # destination_location = fields.Text(string="Destination Location", compute='_compute_location_info', store=True)

    # @api.depends('location.source', 'location.source_province', 'location.source_district',
    #              'location.source_palika', 'location.source_ward',
    #              'location.destination', 'location.destination_province',
    #              'location.destination_district', 'location.destination_palika',
    #              'location.destination_ward')
    # def _compute_location_info(self):
    #     for record in self:
    #         source_parts = []
    #         destination_parts = []
    #         for loc in record.location:
    #             source = ", ".join(filter(None, [
    #                 loc.source_province.name if loc.source_province else '',
    #                 loc.source_district.district_name if loc.source_district else '',
    #                 loc.source_palika.palika_name if loc.source_palika else '',
    #                 loc.source_ward and f"Ward {loc.source_ward}",
                    
    #             ]))
    #             destination = ", ".join(filter(None, [
    #                 loc.destination_province.name if loc.destination_province else '',
    #                 loc.destination_district.district_name if loc.destination_district else '',
    #                 loc.destination_palika.palika_name if loc.destination_palika else '',
    #                 loc.destination_ward and f"Ward {loc.destination_ward}", 
    #             ]))
    #             source_parts.append(source)
    #             destination_parts.append(destination)

    #         record.source_location = "\n".join(source_parts)
    #         record.destination_location = "\n".join(destination_parts)
    # @api.depends('weight','per_unit_price','tax')
    # @api.onchange('weight','per_unit_price','tax')
    # def _compute_untaxed_total_price(self):
    #     for rec in self:
    #         rec.untaxed_total_price = rec.weight * rec.per_unit_price if rec.weight and rec.per_unit_price else 0.0
    # @api.depends('untaxed_total_price','tax')
    # @api.onchange('untaxed_total_price','tax')
    # def _compute_total_price(self):
    #     for rec in self:
    #         if rec.tax or 0.0:
    #             tax_rate = rec.tax.amount if rec.tax else 0.0  # tax.amount is typically a percentage (e.g., 13 for 13%)
    #             tax_multiplier = tax_rate / 100
    #             rec.taxed_total_price = rec.untaxed_total_price * (1 + tax_multiplier)
    #         else:
    #             rec.taxed_total_price = rec.untaxed_total_price
    @api.depends('quantity', 'converter','unit') 
    def _compute_total(self):
        for rec in self:
            if rec.converter:
                print("rec.quantity", rec.converter.uom_type)
                if rec.quantity:     
                    if rec.converter.uom_type == rec.unit.uom_type == "reference":
                        rec.weight = float(rec.quantity)        
                    if rec.converter.uom_type == 'smaller':
                        rec.weight = round(float(rec.quantity / rec.converter.ratio), 3)
                    elif rec.converter.uom_type == 'bigger':
                        rec.weight = float(rec.quantity * rec.converter.ratio)
                    elif rec.converter.uom_type == 'reference':
                        rec.weight = float(rec.quantity)
                else:
                    rec.weight = 0.0
            else:
                rec.weight = 0.0
    @api.onchange('quantity', 'unit', 'converter')
    def _onchange_compute_total(self):
        self._compute_total()
        
    # @api.model
    # def open_location_form(self):
    #     print("Here")
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Location',
    #         'view_mode': 'form',
    #         'res_model': 'request.location',
    #         'res_id': self.location.id,
    #         'target': 'new',  # open in popup
    #     }
    


class CleanupAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def cleanup_old_csv_attachments(self):
        cutoff = datetime.now() - timedelta(hours=1)  # or `days=1`
        old_attachments = self.search([
            ('create_date', '<', cutoff),
            ('res_model', '=', 'report.wizard'),
        ])
        old_attachments.unlink()
