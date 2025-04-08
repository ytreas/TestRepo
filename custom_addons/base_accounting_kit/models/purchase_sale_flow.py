from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        result = super(PurchaseOrder, self).button_confirm()

        for order in self:
            vendor_partner = order.partner_id
            related_company = vendor_partner.ref_company_ids and vendor_partner.ref_company_ids[0]
            current_company = self.env.company
            print("Current Company:", current_company)

            partner = self.env['res.partner'].search([
                ('ref_company_ids', 'in', current_company.id)
            ])

            if partner:
                print("Partner found:", partner.name)
            else:
                print("No partner found with the current company.")
            fiscal_year = self.env['account.fiscal.year'].sudo().search([
                ('date_from', '<=', order.date_order),
                ('date_to', '>=', order.date_order),
                ('company_id', '=', 1)
            ], limit=1)
            sale_order_vals = {
                'partner_id': partner.id,
                'origin': order.name,
                'date_order': order.date_order,
                'order_line': [],
                'fiscal_year': fiscal_year.id,
            }
            for line in order.order_line:
                sale_order_vals['order_line'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    'product_uom': line.product_uom.id,
                }))

            user = self.env.user

            # Check if the user has admin access
            is_admin = user.has_group('base.group_system')

            user.company_ids = [(4, related_company.id)]
            if related_company:
                print("Related Company:", related_company)
                sale_order=self.env['sale.order'].with_company(related_company).create(sale_order_vals)
            else:
                sale_order=self.env['sale.order'].create(sale_order_vals)
            print("Sale Order Created:", sale_order)
            # Remove the company only if the user is not an admin
            if not is_admin:
                user.company_ids = [(3, related_company.id)]

        return result

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        """Trigger notification when a new Stock Move is created"""
        stock_move = super(StockMove, self).create(vals)
        message = f"Stock Move {stock_move.reference or stock_move.id} has been created."
        stock_move._create_notification(message)
        return stock_move

    def write(self, vals):
        """Trigger notification when state changes"""
        for record in self:
            old_state = record.state
            res = super(StockMove, record).write(vals)

            new_state = record.state
            if 'state' in vals and old_state != new_state:
                message = f"Stock Move {record.reference or record.id} has changed status to {new_state}."
                record._create_notification(message)

            return res

    def _create_notification(self, message):
        """Helper function to send notifications"""
        self.env['notification.notification'].create_notification(
            message=message,
            model='stock.move',
            record_id=self.id,
            user_id=self.create_uid.id  # Assign notification to the user who created the move
        )