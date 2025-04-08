# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime,date
from dateutil import parser
from dateutil.relativedelta import relativedelta

from collections import defaultdict
import pdfkit
from reportlab.pdfgen import canvas
import json
import base64


class InterCompanyTransferLine(models.Model):
    """
    Model for inter company transfer lines.
    @author: Maulik Barad.
    """
    _name = "inter.company.transfer.line.ept"
    _description = "Inter Company Transfer Line"

    inter_company_transfer_id = fields.Many2one("inter.company.transfer.ept")
    product_id = fields.Many2one("product.product")
    uom = fields.Many2one("uom.uom", related="product_id.uom_id")
    quantity = fields.Float(default=1.0)
    delivered_qty = fields.Float(compute="_compute_delivered_qty", string="Delivered Quantity", store=True,
                                 readonly=True, digits="Product Unit of Measure")
    price = fields.Float("Rate")
    lot_serial_ids = fields.Many2many("stock.lot", string="Lot/Serial", copy=False)
    purchase_line_ids = fields.One2many("purchase.order.line", "ict_line_id", copy=False)

    invoice_ids = fields.One2many("account.move", related="inter_company_transfer_id.invoice_ids", string="Invoices")
    ict_code = fields.Char(related="inter_company_transfer_id.name", string="ICT")
    state = fields.Selection([("draft", "Draft"), ("processed", "Processed"), ("cancel", "Cancelled")], copy=False,
                             default="draft", help="State of ICT.", tracking=True, related="inter_company_transfer_id.state", string="State")
    # corresponding_service_charge = fields.Many2one("inter.company.transfer.ept", related="inter_company_transfer_id.corresponding_service_charge", string="Invoices")
    src_company_id = fields.Many2one('res.company', related="inter_company_transfer_id.src_company_id", string="Farmer's Name", store=True)
    farmerid = fields.Char(string="Farmer ID", compute='_compute_farmer_id', store=True)  # New computed field
    inter_company_subsidy= fields.Float(string="Subsidy", compute="_compute_inter_company_subsidy", store=True)
    inter_company_service_charge_calc = fields.Float(string="Service Charge", compute="_compute_inter_company_service_charge_calc", store=True)

    @api.depends('src_company_id')
    def _compute_farmer_id(self):
        for record in self:
            record.farmerid = record.src_company_id.farmerid 
    dst_company_id = fields.Many2one('res.company', related="inter_company_transfer_id.dst_company_id", string="Buyer", store=True)
    transaction_date = fields.Date(string="Transaction Date", related="inter_company_transfer_id.transaction_date")
    transaction_date_bs = fields.Char(string="Transaction Date BS")

    nyear = fields.Char("Nepali Year", related="inter_company_transfer_id.nyear")
    nmonth = fields.Char("Nepali Month", related="inter_company_transfer_id.nmonth")
    nday = fields.Char("Nepali Day", related="inter_company_transfer_id.nday")
    newyear = fields.Char("Nepali Year", compute="_compute_nepali_year", store=True)

    def _compute_nepali_year(self):
        for record in self:
            record.newyear = record.nyear

    newmonth = fields.Char("Nepali Month", compute="_compute_nepali_month", store=True)

    def _compute_nepali_month(self):
        for record in self:
            record.newmonth = record.nmonth

    newday = fields.Char("Nepali Day", compute="_compute_nepali_day", store=True)

    def _compute_nepali_day(self):
        for record in self:
            record.newday = record.nday

    @api.depends('sub_total', 'transaction_date')
    def _compute_inter_company_subsidy(self):
        for rec in self:
            threshold_date = date(2023, 7, 17)
            if rec.transaction_date and rec.transaction_date <= threshold_date:
                rec.inter_company_subsidy = rec.sub_total * 0.1
            else:
                rec.inter_company_subsidy = rec.sub_total * 0.05
    
    is_calculated_service_charge = fields.Boolean(string="Is serive Charge Calculated", related="inter_company_transfer_id.is_calculated_service_charge")
    # service_charge = fields.Float(string="Service Charge", compute="_compute_service_charge", store=True, readonly=False)
    delivery_charge = fields.Float(string="Delivery Charge", compute="_update_delivery_charge", store=True, readonly=False)
    sub_total = fields.Float(string="Sub Total", compute="_compute_sub_total", store=True)
    total = fields.Float(string="Total", compute="_compute_total", store=True)

    @api.depends('price', 'quantity', 'inter_company_service_charge_calc', 'delivery_charge')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.sub_total - rec.inter_company_service_charge_calc - rec.delivery_charge

    @api.depends('price', 'quantity')
    def _compute_sub_total(self):
        for rec in self:
            rec.sub_total = (rec.price * rec.quantity)

    @api.depends('total')
    def _update_delivery_charge(self):
        for rec in self:
            if not rec.is_calculated_service_charge and rec.sub_total and rec.inter_company_service_charge_calc and rec.total:
                rec.delivery_charge = rec.sub_total - rec.inter_company_service_charge_calc - rec.total
            else:
                rec.delivery_charge = 0.0

    # @api.depends('transaction_date','sub_total')
    # def _compute_service_charge(self):
    #     for rec in self:
    #         if rec.transaction_date <= date(2023, 7, 16):
    #             rec.service_charge = rec.sub_total * 0.08
    #         elif rec.transaction_date >= date(2023, 7, 17):
    #             rec.service_charge = rec.sub_total * 0.04

    @api.depends('transaction_date', 'sub_total')
    def _compute_inter_company_service_charge_calc(self):
        for rec in self:
            threshold_date = date(2023, 7, 17)
            if rec.transaction_date and rec.transaction_date <= threshold_date:
                rec.inter_company_service_charge_calc = rec.sub_total * 0.08
            else:
                rec.inter_company_service_charge_calc = rec.sub_total * 0.04

    @api.constrains("quantity", "lot_serial_ids")
    
    def _check_quantity(self):
        """
        Constraint for checking the quantity.
        @author: Maulik Barad on Date 22-Jan-21.
        """
        for line in self:
            if not line.quantity > 0:
                raise ValidationError(_("Quantity can't be zero or negative."))
            if line.lot_serial_ids and line.product_id.tracking == "serial":
                if line.quantity > len(line.lot_serial_ids):
                    raise ValidationError(_("Provided Serial numbers can't fulfill the given Quantity for Product - "
                                            "%s.\nAdd more Serial numbers to fulfill the quantity.") %
                                          line.product_id.name)

    @api.depends("inter_company_transfer_id.picking_ids.state", "purchase_line_ids.qty_received")
    def _compute_delivered_qty(self):
        """
        Method for counting the delivered quantity.
        @author: Maulik Barad.
        """
        for line in self:
            ict = line.inter_company_transfer_id
            if ict.type == "ict":
                delivered_qty = 0.0
                for po_line in line.purchase_line_ids:
                    delivered_qty += po_line.qty_received
                line.delivered_qty = delivered_qty
            else:
                delivered_qty = 0.0
                for picking in ict.picking_ids.filtered(
                        lambda x: x.state == "done" and x.picking_type_id.code == "incoming"):
                    for move_line in picking.move_line_ids.filtered(lambda x: x.product_id == line.product_id):
                        if not line.lot_serial_ids or (line.lot_serial_ids and move_line.lot_id.name in
                                                       line.lot_serial_ids.mapped("name")):
                            delivered_qty += move_line.qty_done
                line.delivered_qty = delivered_qty

    @api.onchange("product_id", "inter_company_transfer_id")
    def default_price_get(self):
        """
        Sets price of product in ICT line.
        @author: Maulik Barad.
        """
        for line in self:
            if line.product_id:
                pricelist_id = line.inter_company_transfer_id.pricelist_id
                if pricelist_id:
                    line.price = pricelist_id._get_product_price(line.product_id, line.quantity)
                else:
                    line.price = line.product_id.lst_price
            else:
                line.price = 0.0

    @api.model
    def generate_report(self,dateFrom,dateTo):
        user = self.env.user
        company = user.company_id
        display_company = {
            'name': company.name_np,
            'street': company.street_np or '',
            'province': company.province.name_np or '',
        }
        if(dateFrom != None and dateTo != None):
            date_from = datetime.strptime(dateFrom, "%Y-%m-%d")
            date_to = datetime.strptime(dateTo, "%Y-%m-%d")
            records = self.search([('transaction_date', '>=', date_from), ('transaction_date', '<=', date_to)])
        else:
            records = self.search([])
            

        grouped_data = defaultdict(lambda: {
            'name': "",
            'farmerid': "",
            'farmerward': "",
            'sub_total': 0.0,
            'delivery_charge': 0.0,
            'service_charge': 0.0,
            'total': 0.0,
            'subsidy': 0.0,
            'transaction_count': 0,  # Added field for counting transactions
        })

        for record in records:
            src_company_id = record.src_company_id.id

            if not grouped_data[src_company_id]['name']:
                grouped_data[src_company_id]['name'] = record.src_company_id.name
            if not grouped_data[src_company_id]['farmerid']:
                grouped_data[src_company_id]['farmerid'] = record.farmerid
            if not grouped_data[src_company_id]['farmerward']:
                farmer_record = self.env['farm.farmer'].search([('ref', '=', record.farmerid)], limit=1)
                grouped_data[src_company_id]['farmerward'] = farmer_record.ward_no

            grouped_data[src_company_id]['sub_total'] += record.sub_total
            grouped_data[src_company_id]['delivery_charge'] += record.delivery_charge
            grouped_data[src_company_id]['service_charge'] += record.inter_company_service_charge_calc
            grouped_data[src_company_id]['total'] += record.total
            grouped_data[src_company_id]['subsidy'] += record.inter_company_subsidy
            grouped_data[src_company_id]['transaction_count'] += 1  # Increment transaction count

        report_data = {
            'display_company': display_company,
            'grouped_data': [
                {
                    'name': data['name'],
                    'farmerid': data['farmerid'],
                    'farmerward': data['farmerward'],
                    'sub_total': data['sub_total'],
                    'delivery_charge': data['delivery_charge'],
                    'service_charge': data['service_charge'],
                    'total': data['total'],
                    'subsidy': data['subsidy'],
                    'transaction_count': data['transaction_count'],  # Include transaction count in report data
                }
                for data in grouped_data.values() if data['farmerid']
            ]
        }

        return json.dumps(report_data)
