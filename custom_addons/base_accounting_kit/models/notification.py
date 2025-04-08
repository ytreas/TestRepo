from odoo import models, fields, api
# from odoo.addons.bus.models.bus import Bus

class Notification(models.Model):
    _name = 'notification.notification'
    _description = 'Custom Notifications'
    _order = 'create_date desc'

    message = fields.Text(string="Message", required=True)
    model = fields.Char(string="Related Model")
    record_id = fields.Integer(string="Record ID")
    user_id = fields.Many2one('res.users', string="Recipient", default=lambda self: self.env.user)
    state = fields.Selection([('unread', 'Unread'), ('read', 'Read')], string="Status", default='unread')

    def mark_as_read(self):
        """Mark the notification as read."""
        self.write({'state': 'read'})

    @api.model
    def create_notification(self, message, model=None, record_id=None, user_id=None):
        """Create a new notification and send it to WebSocket."""
        user_id = user_id or self.env.user.id
        notification = self.create({
            'message': message,
            'model': model,
            'record_id': record_id,
            'user_id': user_id,
        })

        # Send to WebSocket
        self.send_to_websocket(notification)

        return notification

    def send_to_websocket(self, notification):
        """Send the notification to the user's WebSocket channel."""
        user_channel = f'notification_channel_{notification.user_id.id}'
        message_data = {
            'id': notification.id,
            'message': notification.message,
            'model': notification.model,
            'record_id': notification.record_id,
            'state': notification.state,
            'create_date': notification.create_date.strftime('%Y-%m-%d %H:%M:%S'),
        }

        # Send message via Odoo's WebSocket system
        self.env['bus.bus']._sendone(user_channel, 'notification', message_data)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        """Trigger notification when a new Sale Order is created"""
        sale_order = super(SaleOrder, self).create(vals)
        message = f"Sale Order {sale_order.name} has been created."
        sale_order._create_notification(message)
        return sale_order

    def write(self, vals):
        """Trigger notification when state changes"""
        for record in self:
            old_state = record.state
            res = super(SaleOrder, record).write(vals)

            new_state = record.state
            if 'state' in vals and old_state != new_state:
                message = f"Sale Order {record.name} has changed status to {new_state}."
                record._create_notification(message)

            return res

    def _create_notification(self, message):
        """Helper function to send notifications"""
        self.env['notification.notification'].create_notification(
            message=message,
            model='sale.order',
            record_id=self.id,
            user_id=self.user_id.id
        )

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def create(self, vals):
        """Trigger notification when a new Purchase Order is created"""
        purchase_order = super(PurchaseOrder, self).create(vals)
        message = f"Purchase Order {purchase_order.name} has been created."
        purchase_order._create_notification(message)
        return purchase_order

    def write(self, vals):
        """Trigger notification when state changes"""
        for record in self:
            old_state = record.state
            res = super(PurchaseOrder, record).write(vals)

            new_state = record.state
            if 'state' in vals and old_state != new_state:
                message = f"Purchase Order {record.name} has changed status to {new_state}."
                record._create_notification(message)

            return res

    def _create_notification(self, message):
        """Helper function to send notifications"""
        self.env['notification.notification'].create_notification(
            message=message,
            model='purchase.order',
            record_id=self.id,
            user_id=self.user_id.id
        )

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        """Trigger notification when a new Account Move is created"""
        account_move = super(AccountMove, self).create(vals)
        message = f"Account Move {account_move.name or account_move.id} has been created."
        account_move._create_notification(message)
        return account_move

    def write(self, vals):
        """Trigger notification when state changes"""
        for record in self:
            old_state = record.state
            res = super(AccountMove, record).write(vals)

            new_state = record.state
            if 'state' in vals and old_state != new_state:
                message = f"Account Move {record.name or record.id} has changed status to {new_state}."
                record._create_notification(message)

            return res

    def _create_notification(self, message):
        """Helper function to send notifications"""
        self.env['notification.notification'].create_notification(
            message=message,
            model='account.move',
            record_id=self.id,
            user_id=self.create_uid.id  # Assign notification to the user who created the move
        )