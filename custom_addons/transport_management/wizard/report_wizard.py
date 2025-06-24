from odoo import models, fields, api, _ 
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from ..models.transport_order import convert_to_bs_date
import nepali_datetime
from nepali_datetime import date as nepali_date
import re
import pandas as pd
import xlsxwriter
import csv 
import io
import base64
import collections
from datetime import date
class WizardReport(models.TransientModel):
    _name = 'report.wizard'
    _description = 'Trip Sheet Wizard'
    
    
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    vehicle_id = fields.Many2one('vehicle.number', string="Vehicle")
    driver_id = fields.Many2one('driver.details', string="Driver")
    helper_id = fields.Many2one('helper.details', string="Helper")
    commodity = fields.Many2one('amp.commodity.master', string="Commodity")
    action_domain = fields.Selection([
        ('trip_sheet', 'Trip Sheet'),
        ('transport_invoice', 'Transport Invoice'),
        ('daily_dispatch','Daily Dispatch'),
        ('delivery_performance','Delivery Performance'),
        ('shipment_history','Customer Shipment History'),
        ('none', 'None'),
    ], string="Action Type", required=True, default='none')
    invoice_id = fields.Many2one("account.move",string="Invoice Id")

    dispatch_filter_selection = fields.Selection([
        ('date_range','Normal Date Range'),
        ('dispatch_date','Dispatched Date Range'),
        ('tracking_number','Tracking Number'),
        ('customer','Customer'),
        ('destination','Destination'),
        ('mode','Mode'),
        ('status','Status')
    ], string="Dispatch Filter", default='date_range')
    
    dispatch_mode = fields.Selection([('road', 'Road'), ('air', 'Air')], string='Mode', default='road')
    dispatch_date_from = fields.Date("Dispatch Date From")
    dispatch_date_to = fields.Date("Dispatch Date To")
    tracking_number = fields.Many2one(
            'transport.order',
            string='Tracking Number')
    customer = fields.Many2one('amp.trader', string="Customer")
    
    destination = fields.Char(string="Destination", size=128)
    dispatch_status = fields.Selection([
        ('dispatch','Dispatched'),
        ('not_dispatched', 'Not Dispatched')
    ], string='Dispatched Status', required=True)
    
    delivery_filter_selection = fields.Selection([
        ('date_range','Date Range'),
        ('tracking_number','Tracking Number'),
        ('origin','Origin'),
        ('destination','Destination'),
        ('schedule_date','Schedule Date Range'),
        ('actual_date','Actual Date Range'),
        ('status','Status'),
        ('delay','Delay Range'),
        ('early','Early Range'),
    ], string="Delivery Filter", default='date_range')
    
    origin = fields.Char(string="Origin", size=128)
    schedule_date_from = fields.Date("Schedule Date From")
    schedule_date_to = fields.Date("Schedule Date To")
    actual_date_from = fields.Date("Actual Date From")
    actual_date_to = fields.Date("Actual Date To")
    delivery_status = fields.Selection([
        ('delivered','Delivered'),
        ('not_delivered','Not Delivered')
    ], string='Delivery Status', default='delivered')

    delay_range = fields.Selection([
        ('1-5','1-5 Days'),
        ('5-10','5-10 Days'),
        ('10','10+ Days'),
    ], string='Delay Range')

    early_range = fields.Selection([
        ('1-5','1-5 Days'),
        ('5-10','5-10 Days'),
        ('10','10+ Days'),
    ], string='Early Range')

    shipment_filter_selection = fields.Selection([
        ('customer','Customer'),
        ('date_range','Date Range'),
        ('tracking_number','Tracking Number'),
        ('shipment_date','Shipment Date Range'),
        ('delivery_date','Delivery Date Range'),
        ('status','Status'),
        ('weights','Weight Range'),
        ('charge','Charge Range')
    ], string="Shipment Filter", default='date_range')

    shipment_status = fields.Selection([
        ('delivered','Delivered'),
        ('on_way','On Way')
    ], string='Shipment Status', default='delivered')
    
    weight_range = fields.Selection([
        ('10-100','1-100 Kg'),
        ('100-500','100-500 Kg'),
        ('500','500+ Kg')
    ], string='Weight Range')

    charge_range = fields.Selection([
        ('0-1000','0-1000 Rs'),
        ('1000-5000','1000-5000 Rs'),
        ('5000','5000+ Rs')
    ], string='Charge Range')
    @api.constrains('date_from', 'date_to','schedule_date_to','actual_date_from')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_("From Date cannot be after To Date."))
            if rec.schedule_date_from and rec.date_to and rec.schedule_date_from > rec.schedule_date_to:
                raise UserError(_("From Date cannot be after To Date."))
    
    @api.constrains('date_from', 'date_to','schedule_date_to','actual_date_from')
    def _check_future_dates(self):
        today = fields.Date.today()
        for record in self:
            if record.date_from and record.date_from > today:
                raise UserError(_("Start date cannot be in the future."))
            if record.date_to and record.date_to > today:
                raise UserError(_("End date cannot be in the future."))
            if record.schedule_date_from and record.schedule_date_from > today:
                raise UserError(_("Schedule start date cannot be in the future."))
            if record.schedule_date_to and record.schedule_date_to > today:
                raise UserError(_("Schedule end date cannot be in the future."))
            if record.actual_date_from and record.actual_date_from > today:
                raise UserError(_("Actual date cannot be in the future."))
            if record.actual_date_to and record.actual_date_to > today:
                raise UserError(_("Actual end date cannot be in the future."))
    def cleanup_attachment(self):
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'report.wizard'),
                ('res_id', '=', self.id),
            ], limit=1)

        if attachment:
            attachment.unlink()
            
    def print(self):
        def format_number(num):
            x = "{:.2f}".format(float(num or 0))
            parts = x.split(".")
            integer_part = parts[0]
            decimal_part = parts[1]

            # Add commas as per Indian number system
            last3 = integer_part[-3:]
            rest = integer_part[:-3]
            if rest:
                rest = re.sub(r'(\d)(?=(\d\d)+$)', r'\1,', rest)
                formatted = rest + ',' + last3
            else:
                formatted = last3
            return formatted + '.' + decimal_part
        for record in self:
            domain = []
            date_from_bs = ''
            date_to_bs = ''
            today_date = nepali_datetime.date.from_datetime_date(fields.Date.today())
            if record.date_from:
                date_from_bs =  nepali_datetime.date.from_datetime_date(record.date_from)
                domain.append(('order_date', '>=', record.date_from))
            if record.date_to:
                domain.append(('order_date', '<=', record.date_to))
                date_to_bs =  nepali_datetime.date.from_datetime_date(record.date_to)
            if record.vehicle_id:
                domain.append(('assignment_ids.vehicle_id', '=', record.vehicle_id.id))
            if record.driver_id:
                domain.append(('assignment_ids.driver_id', '=', record.driver_id.id))
            if record.commodity:
                domain.append(('request_details_ids.items.product_id', '=', record.commodity.id))
            if record.helper_id:
                domain.append(('assignment_ids.helper_id', '=', record.helper_id.id))
            if record.invoice_id:
                domain.append(('request_line_id.invoice_id.id', '=', record.invoice_id.id))
                
                
            if record.action_domain == 'daily_dispatch':
                if record.dispatch_filter_selection == 'tracking_number':
                    domain.append(('tracking_number','=',record.tracking_number.tracking_number))
                elif record.dispatch_filter_selection == 'dispatch_date':
                    if record.dispatch_date_from and record.dispatch_date_to:
                        dispatch_date_from_bs =  nepali_datetime.date.from_datetime_date(record.dispatch_date_from)
                        dispatch_date_to_bs =  nepali_datetime.date.from_datetime_date(record.dispatch_date_to)
                        domain.append(('dispatched_date', '>=', dispatch_date_from_bs))
                        domain.append(('dispatched_date', '<=', dispatch_date_to_bs))
                    else:
                        raise UserError(_("Enter From and To Date."))
                elif record.dispatch_filter_selection == 'customer':
                    domain.append(('customer_name','=',record.customer.id))
                elif record.dispatch_filter_selection == 'destination':
                    domain.append(('delivery_location','=',record.destination))
                # elif record.dispatch_filter_selection == 'mode':
                #     domain.append(('mode','=',record.mode))
                #                 elif record.dispatch_filter_selection == 'origin':
                elif record.dispatch_filter_selection == 'status':
                    if record.dispatch_status == 'dispatch':
                        domain.append(('state', '=', 'in_transit'))
                    elif record.dispatch_status == 'not_dispatched':
                        domain.append(('state', '!=', 'process'))
            if record.action_domain == 'delivery_performance':
                if record.delivery_filter_selection == 'tracking_number':
                    domain.append(('tracking_number','=',record.tracking_number.tracking_number))
                elif record.delivery_filter_selection == 'origin':
                    domain.append(('pickup_location','=',record.origin))
                elif record.delivery_filter_selection == 'destination':
                    domain.append(('delivery_location','=',record.destination))
                elif record.delivery_filter_selection == 'schedule_date':
                    if record.schedule_date_from and record.schedule_date_to:
                        domain.append(('scheduled_date_to', '<=', record.schedule_date_to))
                        domain.append(('scheduled_date_from', '>=', record.schedule_date_from))
                    else:
                        raise UserError(_("Enter From and To Date."))
                elif record.delivery_filter_selection == 'actual_date':
                    if record.actual_date_from and record.actual_date_to:
                        domain.append(('actual_delivery_date', '>=', record.actual_date_from))
                        domain.append(('actual_delivery_date', '<=', record.actual_date_to))
                    else:
                        raise UserError(_("Enter From and To Date."))
                elif record.delivery_filter_selection == 'status':
                    if record.delivery_status == 'delivered':
                        domain.append(('state', '=', 'delivered'))
                    elif record.dispatch_status == 'not_delivered':
                        domain.append(('state', '!=', 'delivered'))
                        
            if record.action_domain == 'shipment_history':
                if record.shipment_filter_selection == 'customer':
                    domain.append(('customer_name','=',record.customer.id))
                elif record.shipment_filter_selection == 'tracking_number':
                    domain.append(('tracking_number','=',record.tracking_number.tracking_number))
                elif record.shipment_filter_selection == 'shipment_date':
                    if record.schedule_date_from and record.schedule_date_to:
                        schedule_date_from_bs =  nepali_datetime.date.from_datetime_date(record.schedule_date_from)
                        schedule_date_to_bs =  nepali_datetime.date.from_datetime_date(record.schedule_date_to)
                        domain.append(('dispatched_date', '>=', schedule_date_from_bs))
                        domain.append(('dispatched_date', '<=', schedule_date_to_bs))
                    else:
                        raise UserError(_("Enter From and To Date."))
                elif record.shipment_filter_selection == 'delivery_date':
                    if record.actual_date_from and record.actual_date_to:
                        domain.append(('actual_delivery_date', '>=', record.actual_date_from))
                        domain.append(('actual_delivery_date', '<=', record.actual_date_to))
                    else:
                        raise UserError(_("Enter From and To Date."))
                elif record.shipment_filter_selection == 'status':
                    if record.shipment_status == 'delivered':
                        domain.append(('state', '=', 'delivered'))
                    elif record.dispatch_status == 'on_way':
                        domain.append(('state', '=', 'in_transit'))
                elif record.shipment_filter_selection == 'charge':
                        if record.charge_range == '0-1000':
                            domain.append(('charge_with_tax','<=',1000))
                        elif record.charge_range == '1000-5000':
                            domain.append(('charge_with_tax','<=',5000))
                        elif record.charge_range == '5000':
                            domain.append(('charge_with_tax','>',5000))
                elif record.shipment_filter_selection == 'weights':
                        if record.weight_range == '10-100':
                            domain.append(('cargo_weight','<=',100))
                        elif record.weight_range == '100-500':
                            domain.append(('cargo_weight','<=',500))
                        elif record.weight_range == '500':
                            domain.append(('cargo_weight','>',500))
                   
                #     domain.append(('pickup_location','=',record.origin))
              
                
            print("Domain",domain)  
            result = self.env['transport.order'].search(domain)
            print(result)
            
            if record.action_domain == 'trip_sheet':
                button_type = self.env.context.get('button_type')
                final_result = []
                for rec in result:
                    commodity_names = ', '.join([commodity.items.product_id.name for commodity in rec.request_details_ids]) if rec.request_details_ids else ''
                    start_date = convert_to_bs_date(rec.scheduled_date_from) if rec.scheduled_date_from else ''
                    end_date = convert_to_bs_date(rec.scheduled_date_to) if rec.scheduled_date_to else ''
                    final_result.append({
                        # 'id':rec.id,
                        'vehicle_number': rec.assignment_ids.vehicle_id.final_number,
                        'driver_name': rec.assignment_ids.driver_id.name,
                        'helper_name': rec.assignment_ids.helper_id.name if rec.assignment_ids.helper_id else '',
                        'start_datetime': ', '.join([start_date if start_date else '',
                                rec.pickup_time if rec.pickup_time else '']),
                        'end_datetime': ', '.join([end_date if end_date else '',
                            rec.delivery_time if rec.delivery_time else '']),

                        'from_location': rec.pickup_location if rec.pickup_location else '',
                        'destination_location': rec.delivery_location if rec.delivery_location else '',
                        'commodity': commodity_names,
                        'weight': rec.cargo_weight,
                        'distance': rec.total_distance,
                        'fuel_use': sum(rec.expense_ids.mapped('fuel_volume')),
                        'remarks': "समयमै डेलिभरी" if rec.pod_id.pod_date >= rec.scheduled_date_from and rec.pod_id.pod_date <= rec.scheduled_date_to else "ढिलो डेलिभरी {}".format(rec.pod_id.pod_date),

                        })
                # print("Final Result:", final_result,date_from_bs,date_to_bs)
                df = pd.DataFrame(final_result)
                if button_type == 'excel':
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    worksheet = workbook.add_worksheet('Trip Sheet Report')
                    bold = workbook.add_format({'bold': True})
                    currency = workbook.add_format({'num_format': '#,##0.00'})
                    headers = list(final_result[0].keys())
                    for col, header in enumerate(headers):
                        worksheet.write(0, col, header, bold)
                    for row_num, row_data in enumerate(final_result, start=1):
                        for col_num, key in enumerate(headers):
                            value = row_data.get(key, '')
                            if hasattr(value, 'strftime'):
                                try:
                                    value = value.strftime('%Y-%m-%d') 
                                except Exception:
                                    pass 

                            worksheet.write(row_num, col_num, value)
                    workbook.close()
                    xlsx_data = output.getvalue()
                    output.close()
                    attachment = self.env['ir.attachment'].create({
                        'name': 'trip_sheet_report.xlsx',
                        'type': 'binary',
                        'datas': base64.b64encode(xlsx_data).decode('utf-8'),
                        'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'res_model': 'report.wizard',  # Change to your actual model if needed
                        'res_id': self.id,
                    })
                    return {
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/%d?download=true' % attachment.id,
                        'target': 'new',
                    }
                    # output = io.StringIO()
                    # writer = csv.DictWriter(output, fieldnames=final_result[0].keys())
                    
                    # writer.writeheader()
                    # writer.writerows(final_result)
                    # csv_data = output.getvalue().encode('utf-8-sig') 
                    # output.close()

                    # # Return the file as a downloadable attachment (file)
                    # attachment = self.env['ir.attachment'].create({
                    #     'name': 'trip_sheet.xlsx',
                    #     'type': 'binary',
                    #     'datas': base64.b64encode(csv_data),
                    #     'mimetype': 'application/vnd.ms-excel',  # CSV MIME type
                    #     'res_model': 'report.wizard',  # Link to wizard
                    #     'res_id': self.id,  # Link to the wizard's record
                    # })
                    # return {
                    #     'type': 'ir.actions.act_url',
                    #     'url': '/web/content/%d?download=true' % attachment.id,
                    #     'target': 'new',
                    # }

                # print(df)
                # df.to_csv("final_result.csv", index=False, encoding='utf-8-sig')
                elif button_type == 'pdf':
                    return {
                            'type': 'ir.actions.report',
                            'report_name': 'transport_management.trip_report_template',
                            'report_type': 'qweb-pdf',
                            'data': {
                                'date_from':date_from_bs,
                                'date_to':date_to_bs,
                                'today_date': today_date,
                                'company_name': self.env.company.name,
                                'report_name': 'Trip Sheet Report',
                                'prepared_data': final_result or [],
                            }
                        }
                
            elif record.action_domain == 'transport_invoice':
                button_type = self.env.context.get('button_type')
                final_result = []
                for rec in result:
                    print("SOUrce loaction and destination location",rec.request_details_ids, rec.delivery_location)
                    vat_name = rec.tax_id.name
                    final_invoice_num = self.env['account.move'].search([('id', '=', rec.request_line_id.invoice_id.id)])
                    if final_invoice_num:
                        print("Invoice Date",final_invoice_num.invoice_date , type(final_invoice_num.invoice_date))
                        invoice_number = final_invoice_num.name
                        invoice_date =  nepali_datetime.date.from_datetime_date(final_invoice_num.invoice_date)
                        invoice_sub_total = final_invoice_num.amount_untaxed
                        # invoice_tax = final_invoice_num.amount_tax f"({final_invoice_num.invoice_line_ids.tax_ids.name})"
                        invoice_total_amount = final_invoice_num.amount_total
                        tax_amount = final_invoice_num.amount_tax
                        tax_label = f"VAT {vat_name}"
                        payment_received = "Not Paid"
                        balance_due = 0.0
                        # print("First",invoice_number)
                        # print("Second",tax_amount,invoice_sub_total)
                        if final_invoice_num.payment_state == 'paid':
                            payment_received = f"{invoice_total_amount}(fully paid)"
                            balance_due = ''
                     
                        elif final_invoice_num.payment_state == 'partial':
                            # payment_received = f"{final_invoice_num.amount_residual}(Advance)"
                            payment_received = f"{final_invoice_num.amount_total - final_invoice_num.amount_residual}(Advance)"
                            balance_due = invoice_total_amount - final_invoice_num.amount_residual_signed
                        # print("$$$$$$$$$$$$$$$$$$$$$$",payment_received ,(final_invoice_num.amount_total - final_invoice_num.amount_residual))
                        commodity_names = ', '.join([commodity.items.product_id.name for commodity in rec.request_details_ids]) if rec.request_details_ids else ''
                        start_date = convert_to_bs_date(rec.scheduled_date_from) if rec.scheduled_date_from else ''
                        end_date = convert_to_bs_date(rec.scheduled_date_to) if rec.scheduled_date_to else ''
                        final_result.append({
                            # 'id':rec.id,
                            'invoice_number':invoice_number,
                            'invoice_date':invoice_date,
                            'sender_name': rec.customer_name.name,
                            'from_location': rec.pickup_location if rec.pickup_location else '',
                            'receiver_name':rec.receiver_name.name,
                            'destination_location': rec.delivery_location if rec.delivery_location else '',
                            'vehicle_number': rec.assignment_ids.vehicle_id.final_number,
                            'driver_name': rec.assignment_ids.driver_id.name,
                            'helper_name': rec.assignment_ids.helper_id.name if rec.assignment_ids.helper_id else '',
                            
                            'start_datetime': ', '.join([start_date if start_date else '',
                                    rec.pickup_time if rec.pickup_time else '']),
                            'end_datetime': ', '.join([end_date if end_date else '',
                                rec.delivery_time if rec.delivery_time else '']),
                            
                            'commodity': commodity_names,
                            'weight': rec.cargo_weight,
                            'charge_type':rec.charge_type.rate_type,
                            'charge_rate':rec.charge_type.unit_price,
                            # 'rate': rec.per_km_rate if  
                            'distance': rec.total_distance,
                            'sub_total':invoice_sub_total,
                            'vat_name':tax_label,
                            'vat_amount':tax_amount,
                            'total':invoice_total_amount,
                            'payment_received':payment_received,
                            'balance_due':balance_due,
                            'fuel_use': rec.expense_ids.fuel_volume,
                            # 'remarks': "समयमै डेलिभरी" if rec.pod_id.pod_date >= rec.scheduled_date_from and rec.pod_id.pod_date <= rec.scheduled_date_to else "ढिलो डेलिभरी {}".format(rec.pod_id.pod_date),
                            'remarks': "डेलिभरी सम्पन्न" if rec.pod_id.pod_date  else "डेलिभरी बाँकी ",

                            })
                
                total_amount = 0.0
                total_due_amount = 0.0
                for result in final_result:
                    total_amount = format_number(round(sum(float(item['total'] or 0) for item in final_result) , 2))
                    total_due_amount = format_number(round(sum(float(item['balance_due'] or 0) for item in final_result) ,2))
                    
                if button_type == 'excel':
                    output = io.BytesIO()

                    # Create the workbook and worksheet
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    worksheet = workbook.add_worksheet('Invoice Report')

                    # Formats
                    bold = workbook.add_format({'bold': True})
                    currency = workbook.add_format({'num_format': '#,##0.00'})

                    # Extract headers from keys of the first dict in final_result
                    headers = list(final_result[0].keys())

                    # Write header row
                    for col, header in enumerate(headers):
                        worksheet.write(0, col, header, bold)

                    # Write data rows
                    for row_num, row_data in enumerate(final_result, start=1):
                        for col_num, key in enumerate(headers):
                            value = row_data.get(key, '')

                            # Convert nepali_datetime.date to string
                            if hasattr(value, 'strftime'):
                                try:
                                    value = value.strftime('%Y-%m-%d')  
                                except Exception:
                                    pass  

                            worksheet.write(row_num, col_num, value)

                    # Prepare total row
                    total_row_index = len(final_result) + 1
                    for col_num, key in enumerate(headers):
                        if key == 'total':
                            worksheet.write(total_row_index, col_num, total_amount, currency)
                        elif key == 'balance_due':
                            worksheet.write(total_row_index, col_num, total_due_amount, currency)
                        elif key.lower() == 'invoice_number':
                            worksheet.write(total_row_index, col_num, 'Total', bold)
                        else:
                            worksheet.write(total_row_index, col_num, '')

                    # Finalize the Excel file
                    workbook.close()
                    xlsx_data = output.getvalue()
                    output.close()

                    # Create the attachment in Odoo
                    attachment = self.env['ir.attachment'].create({
                        'name': 'invoice_report.xlsx',
                        'type': 'binary',
                        'datas': base64.b64encode(xlsx_data).decode('utf-8'),
                        'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'res_model': 'report.wizard',  
                        'res_id': self.id,
                    })
                    return {
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/%d?download=true' % attachment.id,
                        'target': 'new',
                    }
                    
                elif button_type == 'pdf':
                    return {
                        'type': 'ir.actions.report',
                        'report_name': 'transport_management.invoice_report_template',
                        'report_type': 'qweb-pdf',
                        'data': {
                            'date_from':date_from_bs,
                            'today_date':today_date,
                            'date_to':date_to_bs,
                            'company_name': self.env.company.name,
                            'report_name': 'Invoice Report',
                            'prepared_data': final_result or [],
                            'total_amount' :total_amount,
                            'total_balance_due': total_due_amount,
                        }
                    }
            elif record.action_domain == 'daily_dispatch':
                button_type = self.env.context.get('button_type')
                grouped_result = collections.defaultdict(list)
                for rec in result:
                    if rec.state in ('in_transit', 'delivered', 'draft'):
                        duty = self.env['duty.allocation'].search([('transport_order', '=', rec.name)], limit=1)
                        dispatch_datetime = duty.start_datetime
                        dispatch_date = (
                                datetime.strptime(duty.start_datetime, '%Y-%m-%d %H:%M:%S').date()
                                if duty.start_datetime else False
                            )

                        if dispatch_date:
                            grouped_result[dispatch_date].append({
                                'dispatch_date': dispatch_datetime,
                                'tracking_number': rec.tracking_number,
                                'customer_name': rec.customer_name.name,
                                'destination': rec.delivery_location,
                                'mode': 'Road',
                                'status': (
                                    'In Transit' if rec.state == 'in_transit'
                                    else 'Dispatched' if rec.state == 'delivered'
                                    else ''
                                ),
                            })
                final_result = [{'dispatch_date': k, 'records': v} for k, v in grouped_result.items()]
                if button_type == 'pdf':
                    return {
                        'type': 'ir.actions.report',
                        'report_name': 'transport_management.daily_dispatch_template',
                        'report_type': 'qweb-pdf',
                        'data': {
                            'date_from':date_from_bs,
                            'today_date':today_date,
                            'date_to':date_to_bs,
                            'company_name': self.env.company.name,
                            'report_name': 'Daily Dispatch Report',
                            'prepared_data': final_result or [],
                        }
                    }
                elif button_type == 'excel':
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    worksheet = workbook.add_worksheet('Daily Dispatch Sheet')  # ✅ THIS LINE IS REQUIRED
                    bold = workbook.add_format({'bold': True})
                    currency = workbook.add_format({'num_format': '#,##0.00'})

                    headers = ['Dispatch Date', 'Tracking Number', 'Customer Name', 'Destination', 'Mode', 'Status']
                    for col, header in enumerate(headers):
                        worksheet.write(0, col, header, bold)

                    row_num = 1
                    for group in final_result:
                        dispatch_date = group['dispatch_date']
                        records = group['records']
                        for record in records:
                            worksheet.write(row_num, 0, dispatch_date.strftime('%Y-%m-%d') if hasattr(dispatch_date, 'strftime') else dispatch_date)
                            worksheet.write(row_num, 1, record.get('tracking_number', ''))
                            worksheet.write(row_num, 2, record.get('customer_name', ''))
                            worksheet.write(row_num, 3, record.get('destination', ''))
                            worksheet.write(row_num, 4, record.get('mode', ''))
                            worksheet.write(row_num, 5, record.get('status', ''))
                            row_num += 1

                    workbook.close()
                    xlsx_data = output.getvalue()
                    output.close()
                    attachment = self.env['ir.attachment'].create({
                        'name': 'trip_sheet_report.xlsx',
                        'type': 'binary',
                        'datas': base64.b64encode(xlsx_data).decode('utf-8'),
                        'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'res_model': 'report.wizard',  # Change to your actual model if needed
                        'res_id': self.id,
                    })
                    return {
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/%d?download=true' % attachment.id,
                        'target': 'new',
                    }
                    # print("Final Result",final_result)
                    
            elif record.action_domain == 'delivery_performance':
                button_type = self.env.context.get('button_type')
                grouped_result = collections.defaultdict(list)
                for rec in result:
                    if rec.state == 'delivered' and isinstance(rec.actual_delivery_date, date) and isinstance(rec.scheduled_date_to, date):
                        delivery_date = rec.actual_delivery_date
                        delta = (delivery_date - rec.scheduled_date_to).days
                        delay_days = delta if delta > 0 else 0
                        early_days = abs(delta) if delta < 0 else 0
                        status = 'On Time'
                        if delta > 0:
                            status = 'Delayed'
                        elif delta < 0:
                            status = 'Early'
                            
                        delivery_date_bs = convert_to_bs_date(delivery_date)
                        status = 'On Time' if delay_days == 0 else 'Delayed'
                        if delivery_date:
                            grouped_result[delivery_date_bs].append({
                            
                                'tracking_number': rec.tracking_number,
                                'origin': rec.pickup_location,
                                'destination': rec.delivery_location,
                                'delivery_date' : rec.scheduled_date_to_bs,
                                'actual_delivery_date':  delivery_date_bs,
                                'status':status,
                                'delay_days':delay_days,
                                'early_days': early_days,
                            })
                final_result = [{'actual_delivery_date': k, 'records': v} for k, v in grouped_result.items()]
                filtered_result = []

                for group in final_result:
                    filtered_records = []
                    for rec in group['records']:
                        delay_days = rec.get('delay_days', 0)
                        # Apply delay range filter only if the status is 'Delayed'
                        if rec['status'] == 'Delayed' and record.delay_range:
                            if record.delay_range == '1-5' and not (1 <= delay_days <= 5):
                                continue
                            elif record.delay_range == '5-10' and not (5 < delay_days <= 10):
                                continue
                            elif record.delay_range == '10' and not (delay_days > 10):
                                continue
                            filtered_records.append(rec)
                        early_days = rec.get('early_days', 0)
                        if rec['status'] == 'Early' and record.early_range:
                            if record.early_range == '1-5' and not (1 <= early_days <= 5):
                                continue
                            elif record.early_range == '5-10' and not (5 < early_days <= 10):
                                continue
                            elif record.early_range == '10' and not (early_days > 10):
                                continue
                            filtered_records.append(rec)

                    # Only add groups with at least one valid record
                    if filtered_records:
                        filtered_result.append({
                            'actual_delivery_date': group['actual_delivery_date'],
                            'records': filtered_records
                        })
                    
                # print("RRRRRRRRRRRRRR",filtered_result,record.delay_range)
                # print("Final Result",final_result)
                if button_type == 'pdf':
                    return {
                        'type': 'ir.actions.report',
                        'report_name': 'transport_management.daily_performance_template',
                        'report_type': 'qweb-pdf',
                        'data': {
                            'date_from':date_from_bs,
                            'today_date':today_date,
                            'date_to':date_to_bs,
                            'company_name': self.env.company.name,
                            'report_name': 'Daily Performance Report',
                            'prepared_data': filtered_result or [],
                            }
                    }
                elif button_type == 'excel':
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    worksheet = workbook.add_worksheet('Daily Performance Sheet')
                    bold = workbook.add_format({'bold': True})
                    currency = workbook.add_format({'num_format': '#,##0.00'})

                    # Define correct headers based on your actual data structure
                    headers = ['Actual Delivery Date', 'Tracking Number', 'Origin', 'Destination', 'Scheduled Delivery Date', 'Status', 'Delay Days', 'Early Days']
                    for col, header in enumerate(headers):
                        worksheet.write(0, col, header, bold)

                    # Flatten and write data rows
                    row_num = 1
                    for group in filtered_result:
                        actual_delivery_date = group['actual_delivery_date']
                        records = group['records']
                        for record in records:
                            worksheet.write(row_num, 0, actual_delivery_date)  # Already a BS date string
                            worksheet.write(row_num, 1, record.get('tracking_number', ''))
                            worksheet.write(row_num, 2, record.get('origin', ''))
                            worksheet.write(row_num, 3, record.get('destination', ''))
                            worksheet.write(row_num, 4, record.get('delivery_date', ''))  # Scheduled delivery in BS
                            worksheet.write(row_num, 5, record.get('status', ''))
                            worksheet.write(row_num, 6, record.get('delay_days', 0))
                            worksheet.write(row_num, 7, record.get('early_days', 0))
                            row_num += 1

                    workbook.close()
                    xlsx_data = output.getvalue()
                    output.close()

                    attachment = self.env['ir.attachment'].create({
                        'name': 'daily_performance_report.xlsx',
                        'type': 'binary',
                        'datas': base64.b64encode(xlsx_data).decode('utf-8'),
                        'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'res_model': 'report.wizard',
                        'res_id': self.id,
                    })

                    return {
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/%d?download=true' % attachment.id,
                        'target': 'new',
                    }

                
            elif record.action_domain == 'shipment_history':
                button_type = self.env.context.get('button_type')
                group_result = collections.defaultdict(list)
                for rec in result:
                    if rec.state in ('process','in_transit','delivered'):
                        shipping_date  = rec.dispatched_date
                        if shipping_date:
                            group_result[shipping_date].append({
                                'customer_name':rec.customer_name.name,
                                'tracking_number':rec.tracking_number,
                                'shipment_date':shipping_date,
                                'delivery_date':convert_to_bs_date(rec.actual_delivery_date),
                                'status':rec.state,
                                'total_weight':rec.cargo_weight,
                                'charges':rec.charge_with_tax,
                            })
                final_result = [{'shipping_date':k,'records':v} for k,v in group_result.items()]
                if button_type == 'pdf':
                    return {
                        'type': 'ir.actions.report',
                        'report_name': 'transport_management.shipment_history_template',
                        'report_type': 'qweb-pdf',
                        'data': {
                            'date_from':date_from_bs,
                            'today_date':today_date,
                            'date_to':date_to_bs,
                            'company_name': self.env.company.name,
                            'report_name': 'Shipment History Report',
                            'prepared_data': final_result or [],
                            }
                    }
                elif button_type == 'excel':
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    worksheet = workbook.add_worksheet('Shipment History')
                    bold = workbook.add_format({'bold': True})
                    currency = workbook.add_format({'num_format': '#,##0.00'})

                    # Define headers based on your data structure
                    headers = [
                        'Shipping Date', 'Customer Name', 'Tracking Number',
                        'Shipment Date', 'Delivery Date (BS)', 'Status',
                        'Total Weight', 'Charges'
                    ]
                    for col, header in enumerate(headers):
                        worksheet.write(0, col, header, bold)

                    # Write the data
                    row_num = 1
                    for group in final_result:
                        shipping_date = group['shipping_date']
                        records = group['records']
                        for record in records:
                            worksheet.write(row_num, 0, shipping_date.strftime('%Y-%m-%d') if hasattr(shipping_date, 'strftime') else shipping_date)
                            worksheet.write(row_num, 1, record.get('customer_name', ''))
                            worksheet.write(row_num, 2, record.get('tracking_number', ''))
                            worksheet.write(row_num, 3, record.get('shipment_date', '').strftime('%Y-%m-%d') if hasattr(record.get('shipment_date'), 'strftime') else record.get('shipment_date', ''))
                            worksheet.write(row_num, 4, record.get('delivery_date', ''))
                            worksheet.write(row_num, 5, record.get('status', ''))
                            worksheet.write(row_num, 6, record.get('total_weight', 0))
                            worksheet.write(row_num, 7, record.get('charges', 0))
                            row_num += 1

                    workbook.close()
                    xlsx_data = output.getvalue()
                    output.close()

                    attachment = self.env['ir.attachment'].create({
                        'name': 'shipment_history_report.xlsx',
                        'type': 'binary',
                        'datas': base64.b64encode(xlsx_data).decode('utf-8'),
                        'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'res_model': 'report.wizard',  # Change if needed
                        'res_id': self.id,
                    })

                    return {
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/%d?download=true' % attachment.id,
                        'target': 'new',
                    }

                # print("FINAL RESULT",final_result)
            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'reload',
            #     'params': {'action': 'reload_page'},
            #     }
        
        
        
   
