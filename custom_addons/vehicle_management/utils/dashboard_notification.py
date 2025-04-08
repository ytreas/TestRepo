from odoo import api, models, _
from markupsafe import Markup
import html

class Utilities():
    def __init__(self, env):
        # Initialize with the Odoo environment
        self.env = env
        
    def showNotificationDashboard(self, date, vehicle_number, renewal_type, driver_name):
        admin_user = self.env.ref("base.user_admin")
        vehicle_number = vehicle_number if vehicle_number else 'N/A'
        driver_name = driver_name if driver_name else 'N/A'
        # Search for or create the channel for vehicle renewal notifications
        admin_channel = self.env["discuss.channel"].search(
            [("name", "=", "Vehicle Renewal Notification")], limit=1
        )


        # If no channel is found, create one
        if not admin_channel:
            admin_channel = self.env["discuss.channel"].create({
                "name": _("Vehicle Renewal Notification"),
                "channel_type": "channel",
                "group_ids": [
                    (
                        4,
                        self.env.ref("vehicle_management.group_vehicle_admin").id
                    )
                ],
                "channel_partner_ids": [(4, admin_user.partner_id.id)],
            })
        mail_data = self._format_renewal_notification(date, vehicle_number, renewal_type,driver_name)
        # Post the message to the channel
        admin_channel.message_post(
            body=mail_data,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=3,  # You might want to change this to a valid user ID
        )
        
        # Action response
        # return {
        #     "effect": {
        #         "fadeout": "slow",
        #         "message": _("Renewal Notification Sent."),
        #         "type": "rainbow_man",
        #     }
        # }

    def _format_renewal_notification(self, date, vehicle_number, renewal_type,driver_name):
        """
        Helper method to generate renewal notification content dynamically.
        """
        renewal_messages = {
            'bluebook': _('Vehicle Bluebook Renewal'),
            'insurance': _('Vehicle Insurance Renewal'),
            'permit': _('Vehicle Permit Renewal'),
            'pollution': _('Vehicle Pollution Renewal'),
            'service': _('Vehicle Service Time'),
            'license': _('Driver License Renewal'),
            # You can add more types here
        }
        if renewal_type == 'service':
            renewal_message = renewal_messages.get(renewal_type, _('Vehicle Service Notification'))
            notification_message = _(
                "The last {renewal_type} for vehicle number {vehicle_number} was on {date}. "
                "Please ensure the {renewal_type} is done promptly to avoid any issues. "
                "The Service Schedule is created so, please service as soon as possible. "
                "Details are provided below."
            ).format(
                renewal_type=renewal_type,
                vehicle_number=vehicle_number if vehicle_number else 'N/A',
                date=date
            )
            mail_data = Markup("""
                <div class="notification-content" style="padding: 10px; border: 1px solid #ccc; border-radius: 5px;">
                    <h3 class="my-1" style="color: #007bff;">{renewal_message}</h3>
                    <p class="my-1">{notification_message}</p>
                    <p class="my-1"><strong>Renewal Type:</strong> {renewal_type}</p>
                    <p class="my-1"><strong>Vehicle Number:</strong> {vehicle_number}</p>
                    <p class="my-1"><strong>Last Service Date:</strong> {date}</p>
                    <p class="my-1" style="color: #d9534f; font-weight: bold;">Please service as soon as possible.</p>
                </div>
            """).format(
                renewal_message=html.escape(renewal_message),
                notification_message=html.escape(notification_message),
                renewal_type=html.escape(renewal_type),
                vehicle_number=html.escape(vehicle_number),
                date=html.escape(date)
            )
        elif renewal_type == 'license':
            renewal_message = renewal_messages.get(renewal_type, _('Driver License Renewal Notification'))
            notification_message = _(
                "The {renewal_type} of driver {driver_name} is expiring soon on {date}. "
                "Please ensure the {renewal_type} is renewed promptly to avoid any issues. "
                "Details are provided below."
            ).format(
                renewal_type=renewal_type,
                vehicle_number = vehicle_number if vehicle_number else 'N/A',
                driver_name=driver_name,
                date= date
            )
            mail_data = Markup("""
                <div class="notification-content" style="padding: 10px; border: 1px solid #ccc; border-radius: 5px;">
                    <h3 class="my-1" style="color: #007bff;">{renewal_message}</h3>
                    <p class="my-1">{notification_message}</p>
                    <p class="my-1"><strong>Renewal Type:</strong> {renewal_type}</p>
                    <p class="my-1"><strong>Driver Name:</strong> {driver_name}</p>
                    <p class="my-1"><strong>License Expiry Date:</strong> {date}</p>
                    <p class="my-1" style="color: #d9534f; font-weight: bold;">Please renew this as soon as possible.</p>
                </div>
            """).format(
                renewal_message=html.escape(renewal_message),
                notification_message=html.escape(notification_message),
                renewal_type=html.escape(renewal_type),
                vehicle_number=html.escape(vehicle_number),
                driver_name=html.escape(driver_name),
                date= date
            )
        else:
            renewal_message = renewal_messages.get(renewal_type, _('Vehicle Renewal Notification'))
            
            notification_message = _(
                "The {renewal_type} for vehicle number {vehicle_number} is expiring soon on {date}. "
                "Please ensure the {renewal_type} is renewed promptly to avoid any issues. "
                "Details are provided below."
            ).format(
                renewal_type=renewal_type,
                vehicle_number=vehicle_number if vehicle_number else 'N/A',
                driver_name=driver_name,
                date=date
            )
            mail_data = Markup("""
                <div class="notification-content" style="padding: 10px; border: 1px solid #ccc; border-radius: 5px;">
                    <h3 class="my-1" style="color: #007bff;">{renewal_message}</h3>
                    <p class="my-1">{notification_message}</p>
                    <p class="my-1"><strong>Renewal Type:</strong> {renewal_type}</p>
                    <p class="my-1"><strong>Vehicle Number:</strong> {vehicle_number}</p>
                    <p class="my-1"><strong>Expiry Date:</strong> {date}</p>
                    <p class="my-1" style="color: #d9534f; font-weight: bold;">Please renew this as soon as possible.</p>
                </div>
            """).format(
                renewal_message=html.escape(renewal_message),
                notification_message=html.escape(notification_message),
                renewal_type=html.escape(renewal_type),
                vehicle_number=html.escape(vehicle_number),
                date=html.escape(date)
            )
        return mail_data