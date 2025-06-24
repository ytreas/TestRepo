from odoo import api, models, _
from markupsafe import Markup

class BaseNotifier:
    """Shared channel‐creation logic."""
    def __init__(self, env):
        self.env = env
        self.admin_user = self.env.ref("base.user_admin")
        self.channel = self._get_or_create_channel()

    def _get_or_create_channel(self):

        chan = self.env["discuss.channel"].search(
            [("name", "=", "Transport Management Notification")], limit=1
        )
        if not chan:
            chan = self.env["discuss.channel"].create({
                "name": _("Transport Management Notification"),
                "channel_type": "channel",
                "channel_partner_ids": [(4, self.admin_user.partner_id.id)],
            })
        return chan

    def post(self, body_html):

        self.channel.message_post(
            body=body_html,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=self.admin_user.id,
        )


class OrderNotifier(BaseNotifier):
    def __init__(self, env, customer_name, pickup_location, delivery_location, date, order_id=None):
        super().__init__(env)
        self.customer = customer_name
        self.pickup = pickup_location
        self.delivery = delivery_location
        self.date = date
        self.order_id = order_id

    def notify(self):
        title = _("New Transport Order")
        link = ""
        if self.order_id:
            url = f"/web#id={self.order_id}&model=transport.order&view_type=form"
            link = Markup(f'<p><a href="{url}" target="_blank">{_("View Order")}</a></p>')
        details = Markup("""
            <ul style="margin:0; padding-left:1.2em; line-height:1.4;">
                <li><strong>%s:</strong> %s</li>
                <li><strong>%s:</strong> %s</li>
                <li><strong>%s:</strong> %s</li>
                <li><strong>%s:</strong> <time datetime="%s">%s</time></li>
            </ul>
        """) % (
            _('Customer'), self.customer,
            _('Pickup Location'), self.pickup,
            _('Delivery Location'), self.delivery,
            _('Date'), self.date, self.date,
        )
        body = Markup("""
             <div style="font-family:Arial,sans-serif;font-size:14px;color:#333;">
                 <h2 style="color:#007bff;margin-bottom:0.5em;">%s</h2>
                 %s
                 %s
             </div>
         """) % (title, details, link)
        self.post(body)

class DutyAllocationNotifier(BaseNotifier):
    def __init__(self, env, customer_name, driver_name, vehicle_number,
                 from_date, to_date, pickup_address, delivery_address, duty_id=None):
        super().__init__(env)
        self.customer        = customer_name
        self.driver          = driver_name
        self.vehicle_number  = vehicle_number
        self.from_date       = from_date
        self.to_date         = to_date
        self.pickup_address  = pickup_address
        self.delivery_address= delivery_address
        self.duty_id         = duty_id

    def notify(self):
        title = _("New Duty Allocation")

        # Build the list of details as Markup
        details = Markup("""
            <ul style="margin:0; padding-left:1.2em; line-height:1.4;">
                <li><strong>%s:</strong> %s</li>
                <li><strong>%s:</strong> %s</li>
                <li><strong>%s:</strong> %s</li>
                <li><strong>%s:</strong> <time datetime="%s">%s</time></li>
                <li><strong>%s:</strong> <time datetime="%s">%s</time></li>
                <li><strong>%s:</strong> %s</li>
                <li><strong>%s:</strong> %s</li>
            </ul>
        """) % (
            _('Customer'),        self.customer,
            _('Driver'),          self.driver or _('N/A'),
            _('Vehicle No.'),     self.vehicle_number or _('N/A'),
            _('Pickup Date'),     self.from_date, self.from_date,
            _('Delivery Date'),   self.to_date,   self.to_date,
            _('Pickup Address'),  self.pickup_address,
            _('Delivery Address'),self.delivery_address,
        )

        # Build the "View Duty" link separately as Markup
        link_html = Markup('')
        if self.duty_id:
            url = f"/web#id={self.duty_id}&model=duty.allocation&view_type=form"
            link_html = Markup(
                '<p style="margin-top:.5em;"><a href="%s" target="_blank">%s</a></p>'
                % (url, _('View Duty Allocation'))
            )

        # Combine title, details, and link
        body = Markup("""
            <div style="font-family:Arial,sans-serif;font-size:14px;color:#333;">
                <h2 style="color:#007bff;margin-bottom:0.5em;">%s</h2>
                %s
                %s
            </div>
        """) % (title, details, link_html)

        self.post(body)

class DeliveryNotifier(BaseNotifier):
    def __init__(self, env, customer_name, driver_name, order_name, vehicle_number, date, pickup_location, delivery_location, order_id=None):
        super().__init__(env)
        self.customer_name = customer_name
        self.driver_name = driver_name
        self.order_name = order_name
        self.vehicle_number = vehicle_number
        self.date = date
        self.pickup = pickup_location
        self.delivery = delivery_location
        self.order_id = order_id

    def notify(self):
        title = _("🚚 Delivery Completed")
        link = ""
        if self.order_id:
            url = f"/web#id={self.order_id}&model=transport.order&view_type=form"
            link = Markup(f'<p><a href="{url}" target="_blank">{_("View Order")}</a></p>')

        details = Markup("""
            <ul style="margin:0; padding-left:1.2em; line-height:1.4;">
                <li><strong>Customer:</strong> %s</li>
                <li><strong>Order:</strong> %s</li>
                <li><strong>Driver:</strong> %s</li>
                <li><strong>Vehicle:</strong> %s</li>
                <li><strong>Pickup:</strong> %s</li>
                <li><strong>Delivery:</strong> %s</li>
                <li><strong>Date:</strong> <time datetime="%s">%s</time></li>
            </ul>
        """) % (
            self.customer_name,
            self.order_name,
            self.driver_name,
            self.vehicle_number,
            self.pickup,
            self.delivery,
            self.date, self.date,
        )

        body = Markup("""
            <div style="font-family:Arial,sans-serif;font-size:14px;color:#333;">
                <h2 style="color:#28a745;margin-bottom:0.5em;">%s</h2>
                %s
                %s
            </div>
        """) % (title, details, link)

        self.post(body)

class ProcessNotifier(BaseNotifier):
    def __init__(self, env, customer_name, driver_name, order_name, vehicle_number, date, pickup_location, delivery_location, order_id=None):
        super().__init__(env)
        self.customer_name = customer_name
        self.driver_name = driver_name
        self.order_name = order_name
        self.vehicle_number = vehicle_number
        self.date = date
        self.pickup = pickup_location
        self.delivery = delivery_location
        self.order_id = order_id

    def notify(self):
        title = _("Order Process")
        link = ""
        if self.order_id:
            url = f"/web#id={self.order_id}&model=transport.order&view_type=form"
            link = Markup(f'<p><a href="{url}" target="_blank">{_("View Order")}</a></p>')

        details = Markup("""
            <ul style="margin:0; padding-left:1.2em; line-height:1.4;">
                <li><strong>Customer:</strong> %s</li>
                <li><strong>Order:</strong> %s</li>
                <li><strong>Driver:</strong> %s</li>
                <li><strong>Vehicle:</strong> %s</li>
                <li><strong>Pickup:</strong> %s</li>
                <li><strong>Delivery:</strong> %s</li>
                <li><strong>Date:</strong> <time datetime="%s">%s</time></li>
            </ul>
        """) % (
            self.customer_name,
            self.order_name,
            self.driver_name,
            self.vehicle_number,
            self.pickup,
            self.delivery,
            self.date, self.date,
        )

        body = Markup("""
            <div style="font-family:Arial,sans-serif;font-size:14px;color:#333;">
                <h2 style="color:#28a745;margin-bottom:0.5em;">%s</h2>
                %s
                %s
            </div>
        """) % (title, details, link)

        self.post(body)

class CancelNotifier(BaseNotifier):
    def __init__(self, env, customer_name,order_name,date, order_id=None):
        super().__init__(env)
        self.customer           = customer_name
        self.order_name         = order_name
        self.date               = date
        self.order_id           = order_id

    def notify(self):
        title = _("Order Cancelled")
        # Build the list of details as Markup
        details = Markup("""
            <ul style="margin:0; padding-left:1.2em; line-height:1.4;">
                <li><strong>%s:</strong> %s</li>
                <li><strong>%s:</strong> %s</li>
                <li><strong>%s:</strong> <time datetime="%s">%s</time></li>
            </ul>
        """) % (
            _('Customer'),self.customer,
            _('Order Name'),self.order_name or _('N/A'),
            _('Date'), self.date,
        )

        # Build the "View Order" link separately as Markup
        link_html = Markup('')
        if self.order_id:
            url = f"/web#id={self.order_id}&model=transport.order&view_type=form"
            link_html = Markup(
                '<p style="margin-top:.5em;"><a href="%s" target="_blank">%s</a></p>'
                % (url, _('View Order'))
            )

        # Combine title, details, and link
        body = Markup("""
            <div style="font-family:Arial,sans-serif;font-size:14px;color:#333;">
                <h2 style="color:#007bff;margin-bottom:0.5em;">%s</h2>
                %s
                %s
            </div>
        """) % (title, details, link_html)

        self.post(body)
# Factory helper
def notify_transport(env, notification_type, **kwargs):
    if notification_type == 'order':
        notifier = OrderNotifier(
            env,
            customer_name   = kwargs['customer_name'],
            pickup_location = kwargs['pickup_location'],
            delivery_location = kwargs['delivery_location'],
            date            = kwargs['date'],
            order_id        = kwargs.get('order_id', None),
        )
    elif notification_type == 'duty_allocation':
        notifier = DutyAllocationNotifier(
            env,
            customer_name     = kwargs['customer_name'],
            driver_name       = kwargs['driver_name'],
            # order_name        = kwargs.get('order_name', ''),
            vehicle_number    = kwargs['vehicle_number'],
            from_date         = kwargs['from_date'],
            to_date           = kwargs['to_date'],
            pickup_address    = kwargs['pickup_location'],
            delivery_address  = kwargs['delivery_location'],
            duty_id           = kwargs.get('duty_id', None),
        )
    elif notification_type == 'delivery':
        notifier = DeliveryNotifier(
            env,
            customer_name     = kwargs['customer_name'],
            driver_name       = kwargs['driver_name'],
            order_name        = kwargs['order_name'],
            vehicle_number    = kwargs['vehicle_number'],
            date              = kwargs['date'],
            pickup_location   = kwargs['pickup_location'],
            delivery_location = kwargs['delivery_location'],
            order_id          = kwargs.get('order_id'),
        )
    elif notification_type == 'process':
        notifier = ProcessNotifier(
            env,
            customer_name     = kwargs['customer_name'],
            driver_name       = kwargs['driver_name'],
            order_name        = kwargs['order_name'],
            vehicle_number    = kwargs['vehicle_number'],
            date              = kwargs['date'],
            pickup_location   = kwargs['pickup_location'],
            delivery_location = kwargs['delivery_location'],
            order_id          = kwargs.get('order_id'),
        )
    elif notification_type == 'cancel':
        notifier = CancelNotifier(
            env,
            customer_name     = kwargs['customer_name'],
            order_name        = kwargs['order_name'],
            date              = kwargs['date'],
            order_id          = kwargs.get('order_id'),
        )
    else:
        raise ValueError("Unknown notification type")
    notifier.notify()
