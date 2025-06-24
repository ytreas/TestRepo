from odoo import models, fields, api, _
import nepali_datetime 
from dateutil.relativedelta import relativedelta
from nepali_datetime import date as nepali_date
from nepali_datetime import datetime as test
import calendar
from datetime import datetime, timedelta, time
import pytz
from odoo.exceptions import UserError
from datetime import date
from dateutil import parser



# Helper function to convert a Gregorian date to Nepali BS date format.
def convert_to_bs_date(date_val):
    if date_val:
        nep_date = nepali_datetime.date.from_datetime_date(date_val)
        return nep_date.strftime('%Y-%m-%d')
    return False

# Function to parse Nepali date
def parse_nepali_date(nepali_date_str):
    # Replace '/' with '-' if necessary
    nepali_date_str = nepali_date_str.replace('/', '-')
    year, month, day = map(int, nepali_date_str.split('-'))
    return nepali_datetime.date(year, month, day) 

# Function to convert Gregorian date to Nepali
def gregorian_to_nepali(gregorian_date):
    return (gregorian_date.year, gregorian_date.month, gregorian_date.day) 

# Helper function to normalize a time string to HH:MM format.
def normalize_time(time_str):
    # If the string already contains a colon, assume it's in HH:MM format.
    if ':' in time_str:
        return time_str
    # Otherwise, assume it's a number representing hours.
    # Convert the string to float.
    hours = float(time_str)
    hr = int(hours)
    # Compute minutes from the fraction part.
    minutes = int(round((hours - hr) * 60))
    # Format it as HH:MM (pad with zero if necessary).
    return f"{hr:02d}:{minutes:02d}"  

class TransportOrder(models.Model):
    _name = 'transport.order'
    _description = 'Transport Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date_from desc, id desc'
    _rec_name = 'name'  # Use the 'name' field as the display name of the record

    # Order reference field with a default value "New"
    name = fields.Char(
        string='Order Reference',
        required=True,
        readonly=True,
        default=lambda self: _('New')
    )
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    # Customer name field with a Many2one relationship to the amp.trader model
    customer_name = fields.Many2one("amp.trader",string="Sender Name", required=True)
    receiver_name = fields.Many2one("amp.trader",string="Receiver Name", required=True)
    # Pickup location address field
    pickup_location = fields.Char(string='Pickup Location')
    pickup_address = fields.Char(string='Pickup Address')
    # Delivery location address field
    delivery_location = fields.Char(string='Delivery Location')
    delivery_address = fields.Char(string='Delivery Address')
    # Cargo weight with a required constraint
    cargo_weight = fields.Float(string='Weight (kg)', required=True)
    # total_valuation = fields.Float(string='Total Valuation', required=True)
    # Cargo type
    cargo_type = fields.Char(string='Cargo Type')
    # Quantity of cargo with a default value of 1
    cargo_qty = fields.Integer(string='Quantity', default=1)
    # Preferred truck selection field with a Many2one relationship to vehicle.number and domain to filter heavy vehicles
    # The domain filters the vehicles to show only those that are either 'truck' or 'mini_truck' or have a vehicle_type of 'heavy'
    preferred_truck_id = fields.Many2one(
        'vehicle.number',
        string='Preferred Truck',
        domain=[
            ('available', '=', True),
            '|',
            ('heavy', 'in', ['truck', 'mini_truck']),
            ('vehicle_type.vehicle_type', '=', 'heavy'),
        ]
    )
    # Assigned truck selection field with a Many2one relationship to vehicle.number and domain to filter heavy vehicles
    # The domain filters the vehicles to show only those that are either 'truck' or 'mini_truck' or have a vehicle_type of 'heavy'
    assigned_truck_id = fields.Many2one(
        'vehicle.number',
        string='Assigned Truck',
        domain=[
            ('available', '=', True),
            '|',
            ('heavy', 'in', ['truck', 'mini_truck']),
            ('vehicle_type.vehicle_type', '=', 'heavy'),
        ]
    )
    # Order date with a default value of today's date
    order_date = fields.Date(
        string='Order Date',
        default=fields.Date.context_today,
        readonly=True
    )
    # Nepali BS formatted date for order date (computed field)
    order_date_bs = fields.Char(
        string='Order Date', compute='_compute_date_bs',store=True
    )
    order_time = fields.Char(string="Order Time",store=True)
    update_date_bs = fields.Char(string="Update Date Time(bs)",store=True)
    update_period  = fields.Char(string="Updated At:",compute = '_compute_updatetime',store=True)
    update_time = fields.Char(string="Update Time",store=True)
    # Scheduled starting date for the transport order
    scheduled_date_from = fields.Date(
        string='Pickup Date', tracking=True
    )
    # Nepali BS formatted date for scheduled from (computed field)
    scheduled_date_from_bs = fields.Char(
        string='Pickup Date', compute='_compute_date_bs' , store=True
    )
    # Scheduled ending date for the transport order
    scheduled_date_to = fields.Date(
        string='Expected Delivery Date', tracking=True, store=True
    )
    # Nepali BS formatted date for scheduled to (computed field)
    scheduled_date_to_bs = fields.Char(
        string='Delivery Date', compute='_compute_date_bs'
    )
    actual_delivery_date = fields.Date(
        string='Actual Delivery Date', tracking=True
    )

    # Pickup time
    pickup_time = fields.Char(string='Pickup Time')
    # Delivery time
    delivery_time = fields.Char(string='Delivery Time')
    # State of the transport order with predefined selection options
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('process','Process'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancel', 'Cancel'),
    ], string='Status', default='draft', tracking=True)
    send_charge = fields.Boolean(string='Send Charge', default=False)
    assignment_type = fields.Selection([
        ('new', 'New'),
        ('existing', 'Existing')
    ], string='Assignment Type', default='new')
    # One2many relationship with transport.assignment
    assignment_ids = fields.One2many(
        'transport.assignment', 'order_id', string='Assignments' ,required=True
    )
    # One2many relationship with transport.manifest
    manifest_ids = fields.One2many(
        'transport.manifest', 'order_id', string='Manifests'
    )
    # Many2one relationship linking a Proof of Delivery record
    pod_id = fields.One2many(
        'transport.pod', 'order_id', string='Proof of Delivery'
    )
    # One2many relationship with transport.expense
    expense_ids = fields.One2many(
        'transport.expense', 'order_id', string='Expenses'
    )
    # Many2one relationship linking a Customer Request
    request_id = fields.Many2one('customer.request', string='Customer Request')
    # Fields to compute date filters
    is_today = fields.Boolean(string='Is Today', compute='_compute_date_filters', store=True) 
    is_this_week = fields.Boolean(string='Is This Week', compute='_compute_date_filters', store=True) 
    is_this_month = fields.Boolean(string='Is This Month', compute='_compute_date_filters', store=True) 

    is_today_ordered = fields.Boolean(string='Is Today Ordered', compute='_compute_date_filters', store=True)
    is_this_week_ordered = fields.Boolean(string='Is This Week Ordered', compute='_compute_date_filters', store=True)
    is_this_month_ordered = fields.Boolean(string='Is This Month Ordered', compute='_compute_date_filters', store=True)

    # New computed field for duration in hours
    duration = fields.Float(
        string='Duration (Hours)',
        compute='_compute_duration',
        store=True,
        help="Duration in hours calculated between the pickup date/time and delivery date/time."
    )
    duration_hours = fields.Char(
        string='Duration (Hours)',
        compute='_compute_duration_hrs',
        store=True
    )
    existing_assignment_ids = fields.One2many('existing.assignment','order_id')
    total_expense = fields.Monetary(
        string='Total Trip Cost',
        compute='_compute_total_expense',
        store=True,
        currency_field='currency_id',
    )
    total_service_charge = fields.Monetary(
        string='Total Service Cost',
        compute='_compute_total_service_charge',
        store=True,
        currency_field='currency_id',
    )
    advance_done = fields.Boolean(string='Advance Done',default=False)
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env['res.currency'].browse(117),
        readonly=True,
    )

    fuel_expense = fields.Monetary(
        string='Fuel Expense',
        compute='_compute_expenses',
        store=True,
        currency_field='currency_id',
    )

    toll_expense = fields.Monetary(
        string='Toll Expense',
        compute='_compute_expenses',
        store=True,
        currency_field='currency_id',
    )

    maintenance_expense = fields.Monetary(
        string='Maintenance Expense',    
        compute='_compute_expenses',
        store=True,
        currency_field='currency_id',
    )

    driver_allowance_expense = fields.Monetary(
        string='Driver Allowance Expense',
        compute='_compute_expenses',
        store=True,
        currency_field='currency_id',
    )
    charge_type = fields.Many2one('transport.billing.rule',string="Charge Type:")
    charge_type_selection = fields.Selection([
        ('fixed',    'Fixed Rate'),
        ('per_km',   'Per KM Rate'),
        ('per_ton',  'Per Ton Rate'),
        ('per_hour', 'Per Hour Rate'),
    ], compute='_compute_rates', store=True)
    percent_to_paid = fields.Selection([
        ('20','20%'),
        ('30','30%'),
        ('40','40%'),
        ('50','50%'),
        ('60','60%'),
    ],string='Advance to be paid')
    flat_amount = fields.Float(string="Flat Amount:")
    tax_id = fields.Many2one('account.tax', string='Tax')
    charge_with_tax = fields.Float(string='Charge with Tax', compute='_compute_total_charge_with_tax', store=True)
    advance_charge = fields.Float(string='Advance Charge', compute='_compute_total_advance_charge', store=True)
    
    fixed_rate    = fields.Float(compute='_compute_rates', store=True)
    per_km_rate   = fields.Float(compute='_compute_rates', store=True)
    per_ton_rate  = fields.Float(compute='_compute_rates', store=True)
    per_hour_rate = fields.Float(compute='_compute_rates', store=True)

    total_distance = fields.Float(string="Total Distance(km):")
    total_time = fields.Float(string="Total Time(Hr):")
    feedback = fields.Text(string="Feedback", readonly=True)

    fiscal_year = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        default=lambda self: self._compute_fiscal_year(),
    )
    request_line_id = fields.Many2one('customer.request.line',string='Request Lines')
    request_details_ids = fields.One2many('customer.request.details','transport_id',string='Request Details')
    tracking_number = fields.Char(
        string='Tracking Number',
        readonly=True,
        copy=False,
        help="Automatically generated when the order is confirmed."
    )
    dispatched_date = fields.Char(string="Dispatched Date")
    cancel_reason = fields.Text(string="Remarks")
    
    
    
    
    has_delayed_pods = fields.Boolean(compute='_compute_has_delayed_pods', store=True)

    @api.depends('pod_id.delayed')
    def _compute_has_delayed_pods(self):
        for order in self:
            order.has_delayed_pods = any(pod.delayed for pod in order.pod_id)
            
    def _generate_tracking_number(self):
        """Generate tracking number as CARGO-NEP-<YYYY>-<NNNNNN>, 
           using the numeric suffix from self.name (e.g. 'ORDER/00042')."""
        self.ensure_one()
        if not self.name or '/' not in self.name:
            raise UserError(_("Cannot extract sequence from order name '%s'") % self.name)

        # extract the digits after the last slash
        num_part = self.name.split('/')[-1]
        try:
            seq = int(num_part)
        except ValueError:
            raise UserError(_("Order name suffix '%s' is not a valid number") % num_part)

        # build the zero-padded six-digit string
        seq_str = str(seq).zfill(6)

        prefix = 'CARGO-NEP'
        year = date.today().year
        return f"{prefix}-{year}-{seq_str}"
    
    @api.depends('charge_type')
    @api.onchange('charge_type')
    def _compute_rates(self):
        for rec in self:
            # zero everything
            rec.fixed_rate = rec.per_km_rate = rec.per_ton_rate = rec.per_hour_rate = 0.0
            rec.charge_type_selection = rec.charge_type.rate_type or False
            print("charge_type_selection",rec.charge_type_selection)

            if rec.charge_type:
                price = rec.charge_type.unit_price
                print("price",price)
                rt = rec.charge_type.rate_type
                print("rt",rt)
                if rt == 'fixed':
                    rec.fixed_rate = price
                elif rt == 'per_km':
                    rec.per_km_rate = price
                elif rt == 'per_ton':
                    rec.per_ton_rate = price
                elif rt == 'per_hour':
                    rec.per_hour_rate = price

    def _compute_fiscal_year(self):
        current_date = fields.Date.today()
        fiscal_year = self.env["account.fiscal.year"].search(
            [("date_from", "<=", current_date), ("date_to", ">=", current_date)],
            limit=1,
        )
        if fiscal_year:
            return fiscal_year.id
        else:
            return False
    # def send_response(self):
    #     response = self.env
    @api.depends('expense_ids')
    def _compute_expenses(self):
        for order in self:
            order.fuel_expense = sum(order.expense_ids.filtered(lambda e: e.expense_type == 'fuel').mapped('amount'))
            order.toll_expense = sum(order.expense_ids.filtered(lambda e: e.expense_type == 'toll').mapped('amount'))
            order.maintenance_expense = sum(order.expense_ids.filtered(lambda e: e.expense_type == 'maintenance').mapped('amount'))
            order.driver_allowance_expense = sum(order.expense_ids.filtered(lambda e: e.expense_type == 'allowance').mapped('amount'))

    
    @api.depends('expense_ids.amount','charge_type.unit_price')
    def _compute_total_expense(self):
        for order in self:
            order.total_expense = sum(order.expense_ids.mapped('amount'))
    
    @api.depends('charge_type_selection',
                 'fixed_rate', 'per_km_rate', 'per_ton_rate', 'per_hour_rate',
                 'total_distance', 'cargo_weight', 'total_time')
    def _compute_total_service_charge(self):
        for rec in self:
            # pick the matching per‑unit rate
            rate = {
                'fixed':    rec.fixed_rate,
                'per_km':   rec.per_km_rate,
                'per_ton':  rec.per_ton_rate,
                'per_hour': rec.per_hour_rate,
            }.get(rec.charge_type_selection, 0.0)
            # print("rate",rate)

            if rec.charge_type_selection == 'fixed':
                rec.total_service_charge = rate
            elif rec.charge_type_selection == 'per_km':
                rec.total_service_charge = rate * rec.total_distance
            elif rec.charge_type_selection == 'per_ton':
                rec.total_service_charge = rate * rec.cargo_weight/1000
            elif rec.charge_type_selection == 'per_hour':
                rec.total_service_charge = rate * rec.total_time
            else:
                rec.total_service_charge = 0.0
            # print("total_service_charge",rec.total_service_charge)
    @api.depends('total_service_charge','tax_id')
    @api.depends('total_service_charge','tax_id')
    def _compute_total_charge_with_tax(self):
        for rec in self:
            if rec.tax_id:
                tax_amount = rec.total_service_charge * (rec.tax_id.amount / 100)
                rec.charge_with_tax = rec.total_service_charge + tax_amount
            else:
                rec.charge_with_tax = rec.total_service_charge
    @api.onchange('charge_with_tax','percent_to_paid','flat_amount')
    @api.depends('charge_with_tax','percent_to_paid' ,'flat_amount')
    def _compute_total_advance_charge(self):
        for rec in self:
            if rec.percent_to_paid and rec.flat_amount:
                raise UserError("You cannot enter both 'Flat Amount' and 'Percent to Paid'. Please choose only one.")
            if rec.percent_to_paid:
                advance_charge = rec.charge_with_tax * (int(rec.percent_to_paid) / 100)
                rec.advance_charge = advance_charge
            elif rec.flat_amount:
                rec.advance_charge = rec.charge_with_tax + rec.flat_amount
            else:
                rec.advance_charge = 0.0
                
    @api.depends('duration')
    def _compute_duration_hrs(self):
        """Compute the duration in days, hours, minutes, and seconds."""
        for rec in self:
            # duration is in hours (float), convert to total seconds
            total_seconds = rec.duration * 3600.0
            # print("total_seconds",total_seconds)
            days = int(total_seconds // (24 * 3600))
            # print("days",days)
            remaining = total_seconds - (days * 24 * 3600)
            hours = int(remaining // 3600)
            # print("hours",hours)
            remaining %= 3600
            minutes = int(remaining // 60)
            # print("minutes",minutes)
            seconds = int(remaining % 60)
            # print("seconds",seconds)

            parts = []
            if days:
                parts.append(f"{days} day{'s' if days > 1 else ''}")
            if hours or days:
                parts.append(f"{hours} hr{'s' if hours != 1 else ''}")
            if minutes:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            if seconds or not parts:
                parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

            rec.duration_hours = ' '.join(parts)

    @api.depends('scheduled_date_from', 'pickup_time', 'scheduled_date_to', 'delivery_time')
    def _compute_duration(self):
        # print("inside compute duration")
        """
        Compute the duration between the pickup and delivery date–time.
        """
        for rec in self:
            # print(f"scheduled_date_from: {rec.scheduled_date_from}, pickup_time: {rec.pickup_time}, scheduled_date_to: {rec.scheduled_date_to}, delivery_time: {rec.delivery_time}")
            if rec.scheduled_date_from and rec.pickup_time and rec.scheduled_date_to and rec.delivery_time:
                try:
                    # print("inside try")
                    # Normalize the input time strings.
                    pickup_time_str = normalize_time(str(rec.pickup_time))
                    delivery_time_str = normalize_time(str(rec.delivery_time))
                    
                    # print(f"Normalized pickup_time: {pickup_time_str}, delivery_time: {delivery_time_str}")

                    # Determine the correct format based on the colon count.
                    pickup_format = '%H:%M:%S' if pickup_time_str.count(':') == 2 else '%H:%M'
                    delivery_format = '%H:%M:%S' if delivery_time_str.count(':') == 2 else '%H:%M'

                    # Parse the normalized time strings.
                    pickup_time_obj = datetime.strptime(pickup_time_str, pickup_format).time()
                    delivery_time_obj = datetime.strptime(delivery_time_str, delivery_format).time()
                    # print(f"pickup_time_obj: {pickup_time_obj}, delivery_time_obj: {delivery_time_obj}")

                    # Combine the dates and times into datetime objects.
                    pickup_datetime = datetime.combine(rec.scheduled_date_from, pickup_time_obj)
                    delivery_datetime = datetime.combine(rec.scheduled_date_to, delivery_time_obj)
                    # print(f"pickup_datetime: {pickup_datetime}, delivery_datetime: {delivery_datetime}")

                    # Calculate the time difference.
                    delta = delivery_datetime - pickup_datetime
                    # print(f"delta: {delta}")

                    # Convert the time difference to total hours.
                    rec.duration = delta.total_seconds() / 3600.0
                    # print(f"duration: {rec.duration}")
                except Exception as e:
                    # print(f"Error: {e}")
                    rec.duration = 0.0
            else:
                rec.duration = 0.0
                # print("No pickup_time or delivery_time provided.")

    # Function to compute date filters
    @api.depends('scheduled_date_to', 'scheduled_date_to_bs', 'order_date', 'order_date_bs')
    def _compute_date_filters(self):
        today = fields.Date.context_today(self)
        # print(f"Today's Date: {today}")
        for record in self:
            # --- scheduled_date_to block ---
            # print(f"Processing Record ID: {record.id}, scheduled_date_to: {record.scheduled_date_to}")
            record.is_today = record.scheduled_date_to == today
            # print(f"is_today: {record.is_today}")
            if record.scheduled_date_to:
                dt_date = fields.Date.from_string(record.scheduled_date_to)
                dt_today = fields.Date.from_string(today)
                start_of_week = dt_today - timedelta(days=(dt_today.weekday() + 1) % 7)
                end_of_week = start_of_week + timedelta(days=6)
                # print(f"Start of Week: {start_of_week}, End of Week: {end_of_week}")
                record.is_this_week = start_of_week <= dt_date <= end_of_week
                # print(f"is_this_week: {record.is_this_week}")

                today_nepali_date = nepali_datetime.date.from_datetime_date(today)
                # print(f"Today's Nepali Date: {today_nepali_date}")
                date_bs_nepali = parse_nepali_date(record.scheduled_date_to_bs)
                # print(f"Scheduled Date's Nepali Date: {date_bs_nepali}")
                start_of_month = today_nepali_date.replace(day=1)
                # print(f"Start of Month (gregorian): {start_of_month}")
                y, m, d = gregorian_to_nepali(start_of_month)
                start_of_month_nepali = nepali_date(y, m, d)
                # print(f"Start of Month (Nepali): {start_of_month_nepali}")
                record.is_this_month = date_bs_nepali >= start_of_month_nepali
                # print(f"is_this_month: {record.is_this_month}")
            else:
                record.is_today = False
                record.is_this_week = False
                record.is_this_month = False

            # --- order_date block ---
            # print(f"Processing Record ID: {record.id}, order_date: {record.order_date}")
            record.is_today_ordered = record.order_date == today
            # print(f"is_today_ordered: {record.is_today_ordered}")
            if record.order_date:
                dt_date = fields.Date.from_string(record.order_date)
                dt_today = fields.Date.from_string(today)
                start_of_week = dt_today - timedelta(days=(dt_today.weekday() + 1) % 7)
                end_of_week = start_of_week + timedelta(days=6)
                # print(f"Start of Week: {start_of_week}, End of Week: {end_of_week}")
                record.is_this_week_ordered = start_of_week <= dt_date <= end_of_week
                # print(f"is_this_week_ordered: {record.is_this_week_ordered}")

                today_nepali_date = nepali_datetime.date.from_datetime_date(today)
                # print(f"Today's Nepali Date: {today_nepali_date}")
                date_bs_nepali = parse_nepali_date(record.order_date_bs)
                # print(f"Order Date's Nepali Date: {date_bs_nepali}")
                start_of_month = today_nepali_date.replace(day=1)
                # print(f"Start of Month (gregorian): {start_of_month}")
                y, m, d = gregorian_to_nepali(start_of_month)
                start_of_month_nepali = nepali_date(y, m, d)
                # print(f"Start of Month (Nepali): {start_of_month_nepali}")
                record.is_this_month_ordered = date_bs_nepali >= start_of_month_nepali
                # print(f"is_this_month_ordered: {record.is_this_month_ordered}")
            else:
                record.is_today_ordered = False
                record.is_this_week_ordered = False
                record.is_this_month_ordered = False

    def recompute_date_filters(self):
        """Force recomputation of date filters on all records."""
        records = self.search([])
        for rec in records:
            rec.write({'scheduled_date_to': rec.scheduled_date_to})
            rec.write({'order_date': rec.order_date})

    # Helper function to reload the page
    def _reload_action(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action': 'reload_page'},
        }

    @api.depends('scheduled_date_from', 'scheduled_date_to')
    def _compute_date_bs(self):
        """
        Compute method to convert scheduled dates to their corresponding 
        Nepali BS date format using the helper function.
        """
        for record in self:
            record.scheduled_date_from_bs = convert_to_bs_date(record.scheduled_date_from)
            record.scheduled_date_to_bs = convert_to_bs_date(record.scheduled_date_to)
            record.order_date_bs = convert_to_bs_date(record.order_date)
    def _compute_manual_order_name(self):
        """
        Helper method to compute a manual order name in the pattern "Order/XXX".

        It searches for the most recently created order, extracts the numerical
        part from the order name (expected in the format Order/XXX), increments it,
        and returns a new name with the number padded to three digits.
        """
        # Retrieve the most recent order based on the highest id
        last_order = self.search([], order="id desc", limit=1)
        if last_order and last_order.name:
            try:
                # Attempt to extract the numerical part from the order name
                last_number = int(last_order.name.split('/')[-1])
            except Exception:
                # If extraction fails, start numbering from 0
                last_number = 0
        else:
            # No previous order found
            last_number = 0
        # Increment the number and pad with zeros to have three digits
        new_number = last_number + 1
        return "Order/" + str(new_number).zfill(5)

    @api.model
    def create(self, vals):
        # Compute a manual order name if the default is still "New"
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self._compute_manual_order_name()
        # Create the transport order record first.
 
        ktm_tz = pytz.timezone("Asia/Kathmandu")
        ktm_now = datetime.now(ktm_tz)
        vals['order_time'] = ktm_now.time()
        
        order = super(TransportOrder, self).create(vals)
        return order

    def write(self, vals):
        # nep_date = test.now()
        # start_dt = parser.isoparse(self.order_datetime_bs) #convert to string to datetime.datetime object
        # end_dt_str  =  nep_date.strftime("%Y-%m-%d %H:%M:%S.%f%z") # strftime = string formatted time , strptime = string parse time(return datetime objecy)
        for record in self:
            if 'state' in vals:
                # Get Kathmandu timezone current datetime
                ktm_tz = pytz.timezone("Asia/Kathmandu")
                ktm_now = datetime.now(ktm_tz)
                ktm_naive = ktm_now.replace(tzinfo=None)
                ktm_date = ktm_naive.date()
                ktm_time = ktm_naive.time()

                nepali_date = nepali_datetime.date.from_datetime_date(ktm_date)
                current_dt = nepali_datetime.datetime(
                    nepali_date.year, nepali_date.month, nepali_date.day,
                    ktm_time.hour, ktm_time.minute, ktm_time.second
                )

                # Parse last update datetime if exists
                # if record.update_date_bs and record.update_time:
                #     try:
                #         prev_year, prev_month, prev_day = map(int, record.update_date_bs.split("-"))
                #         prev_date = nepali_datetime.date(prev_year, prev_month, prev_day)
                #         prev_time = datetime.strptime(record.update_time, "%H:%M:%S")

                #         prev_dt = nepali_datetime.datetime(
                #             prev_date.year, prev_date.month, prev_date.day,
                #             prev_time.hour, prev_time.minute, prev_time.second
                #         )

                #         delta = current_dt - prev_dt
                #         days = delta.days
                #         hours, remainder = divmod(delta.seconds, 3600)
                #         minutes, seconds = divmod(remainder, 60)

                #         update_period = f"{days} days, {hours} hours, {minutes} minutes"

                #     except Exception as e:
                #         update_period = "Error"

                # else:
                #     update_period = "0 days, 0 hours, 0 minutes"

                # vals['update_period'] = update_period
                # vals['update_date_bs'] = nepali_date.strftime("%Y-%m-%d")
                # vals['update_time'] = ktm_time.strftime("%H:%M:%S")
                
        result = super(TransportOrder, self).write(vals)
        if 'assignment_ids' in vals or 'manifest_ids' in vals:
            self._update_manifest_records()
        return result

    @api.depends('write_date','update_time')
    def _compute_updatetime(self):
        for record in self:
            ktm_tz = pytz.timezone("Asia/Kathmandu")
            ktm_now = datetime.now(ktm_tz)
            ktm_naive = ktm_now.replace(tzinfo=None)

            ktm_date = ktm_naive.date()
            ktm_time = ktm_naive.time()
            
            # date_only = record.write_date.date()
            # update_date_bs = convert_to_bs_date(date_only)
            # record.update_date_bs = update_date_bs

            # year, month, day = map(int, record.update_date_bs.split("-"))
            # start_date = nepali_datetime.date(year, month, day)
            # start_time = datetime.strptime(record.update_time, "%H:%M:%S")
            
    
            # start_dt = nepali_datetime.datetime(
            #     start_date.year, start_date.month, start_date.day,
            #     start_time.hour, start_time.minute, start_time.second
            # )
            # start_dt_naive = start_dt.replace(tzinfo=None)

            # nepali_date = nepali_datetime.date.from_datetime_date(ktm_date)
            # nepali_dt = nepali_datetime.datetime(
            #     nepali_date.year,
            #     nepali_date.month,
            #     nepali_date.day,
            #     ktm_time.hour,
            #     ktm_time.minute,
            #     ktm_time.second,
            #     # ktm_time.microsecond
            # )
            # end_dt_naive = nepali_dt.replace(tzinfo=None)
            # print("ENDDD",end_dt_naive,start_dt_naive)
            # delta = end_dt_naive - start_dt_naive
            
            # print("DElta",delta)
            # days = delta.days
            # hours, remainder = divmod(delta.seconds, 3600)
            # minutes, seconds = divmod(remainder, 60)
            # record.update_period = f"{days} days, {hours} hours, {minutes} minutes"
            record.update_period = f"{ktm_date}, {ktm_time}"
            # record.update_date_bs = update_date_bs
            #record.update_time = ktm_time

    def _update_manifest_records(self):
        """
        Create or update the associated transport.manifest and transport.manifest.line
        records based on the current transport order details.
        """
        for order in self:
            if order.assignment_ids:
                assignment = order.assignment_ids.id
            else:
                assignment = order.existing_assignment_ids
            # Update or create manifest:
            if order.manifest_ids:
                manifest = order.manifest_ids[0]
                manifest.write({
                    'generated_date': fields.Date.today(),
                })
            else:
                manifest = self.env['transport.manifest'].create({
                    'order_id': order.id,
                    'assignment_id':assignment,
                    'generated_date': fields.Date.today(),
                })
            
            # Prepare manifest line values:
            manifest_line_vals = {
                'manifest_id': manifest.id,
                'sequence': 1,
                'description': f"Transport from {order.pickup_location or 'N/A'} to {order.delivery_location or 'N/A'}",
                'cargo_weight': order.cargo_weight,
                'cargo_qty': order.cargo_qty,
                'cargo_type': order.cargo_type,
                'eta': order.scheduled_date_from,
            }
            
            # Update or create manifest line:
            if manifest.line_ids:
                # Update the first manifest line for simplicity.
                manifest.line_ids[0].write(manifest_line_vals)
            else:
                self.env['transport.manifest.line'].create(manifest_line_vals)
            
            
    def action_confirm(self):
        """Action method to set the order state to 'confirmed' and create manifest records."""
        if self.state == 'draft':
            print("Assignment_id",self.assignment_ids)
            ktm_tz = pytz.timezone("Asia/Kathmandu")
            ktm_now = datetime.now(ktm_tz)
            ktm_naive = ktm_now.replace(tzinfo=None)

            ktm_date = ktm_naive.date()
            self.update_time = ktm_naive.time()
            # self.env['transport.assignment'].createRecord(self.assignment_ids)
            # self.advance_done = True
            # Create the manifest when the order is confirmed.
            if self.advance_done == False:
                raise UserError(_("Please make the advance payment before confirming the order."))
            elif self.assignment_ids:
                self._update_manifest_records()
                self.state = 'confirmed'
                self.tracking_number = self._generate_tracking_number()
                print("Tracking Number:", self.tracking_number)
                request = self.env['customer.request'].search([('id', '=', self.request_id.id)],order='id desc', limit=1)
                request_line = self.env['customer.request.line'].search([('id', '=', self.request_line_id.id)],order='id desc', limit=1)
                if request_line:
                    request_line.state = 'accept'
                if request:
                    request.state = 'accept'
            else:
                raise UserError(_("Please make assignment before confirming the order."))
        else:
            raise UserError(_("Order is already confirmed."))
        return self._reload_action()
    
    
    def send_charge_details(self):
        for record in self:
            request_line = self.env['customer.request.line'].search([('id', '=', record.request_line_id.id)],order='id desc', limit=1)
            if request_line:
                request_line.total_charge = record.total_service_charge
                advance_charge = record.charge_with_tax * int(record.percent_to_paid)/100
                request_line.advance_amount = advance_charge
                request_line.tax_id = record.tax_id.id
                request_line.total_charge_with_tax = record.charge_with_tax
                record.send_charge = True
                print("##################3",record.tax_id.id)
                partner = self.env['res.partner'].search([('name', '=', record.customer_name.name)], limit=1)
                due_date = fields.Date.today() + timedelta(days=7)
                invoice_vals = {
                    'move_type': 'out_invoice',  # Customer invoice
                    'partner_id': partner.id,
                    'invoice_date': fields.Date.today(),
                    'invoice_date_due': due_date,
                    'invoice_line_ids': [
                        (0, 0, {
                            'name': "Transport Charge",
                            'quantity': 1.0,
                            'price_unit': record.total_service_charge,
                            'tax_ids':[(6, 0, [record.tax_id.id])],
                            'account_id': 360,  # Revenue account
                        }),
                    ],
                }

                invoice = self.env['account.move'].create(invoice_vals)
                invoice.action_post()
                record.request_line_id.write({
                        'invoice_id': invoice.id,
                        # 'payment_state': 'advance',
                })
                mail_values = {
                'subject': 'Advance Payment Request for Order %s' % self.name,
                'body_html': (
                    f'<p>Dear {self.customer_name.name},</p>'
                    f'<p>We are pleased to inform you that your order <strong>{self.name}</strong> has been successfully placed.</p>'
                    f'<p>To proceed with the fulfillment and delivery of your order, we kindly request an advance payment as per our agreement.</p>'
                    f'<p>Please find the details below:</p>'
                    f'<ul>'
                    f'    <li><strong>Order Number:</strong> {self.name}</li>'
                    f'    <li><strong>Advance Amount:</strong> {self.advance_charge}</li>'
                    f'    <li><strong>Total Amount:</strong> {self.charge_with_tax}</li>'
                    f'    <li><strong>Payment Due:</strong> {due_date}</li>'
                    f'</ul>'
                    f'<p>You may proceed with the payment through the portal</p>'
                    f'<p>If you have any questions or need further assistance, please do not hesitate to contact us.</p>'
                    f'<p>Thank you for choosing our services.</p>'
                    f'<p>Best regards,</p>'
                    f'<p>{self.env.company.name}</p>'
                ),
                'email_to': self.customer_name.email,
                'model': 'transport.order',
                'res_id': self.id,
            }

                    # attachment_ids = []
                    # if self.image_signature:
                    #     attachment = self.env['ir.attachment'].create({
                    #         'name': 'Receiver Signature - %s.png' % order_name,
                    #         'type': 'binary',
                    #         'datas': self.signature,  # Already base64-encoded
                    #         'res_model': self._name,
                    #         'res_id': self.id,
                    #         'mimetype': 'image/png',
                    #     })
                    #     attachment_ids.append((4, attachment.id))
                    # if attachment_ids:
                    #     mail_values['attachment_ids'] = attachment_ids

     
                mail = self.env['mail.mail'].create(mail_values)
                mail.send() 
        # return self._reload_action()
    # def generate_final_invoice(self):
    #     for record in self:
    #         result = self.env['account.move'].search([('id','=',record.request_line_id.final_invoice_id.id)], limit=1)
    #         print("result",result.id)
    #         if result:
    #             raise UserError("Invoice is Already Created")
    #         if record.total_service_charge <= 0:
    #             raise UserError("Total amount must be greater than 0.")
    #         partner = self.env['res.partner'].search([('name', '=', record.customer_name.name)], limit=1)
    #         advance_charge = record.total_service_charge * int(record.percent_to_paid)/100
    #         final_invoice_vals = {
    #             'move_type': 'out_invoice',
    #             'partner_id': partner.id,
    #             'invoice_date': fields.Date.today(),
    #             'invoice_date_due': fields.Date.today() + timedelta(days=7),
    #             'invoice_line_ids': [
    #                 (0, 0, {
    #                     'name': "Transport Charge",
    #                     'quantity': 1.0,
    #                     'price_unit': record.total_service_charge,
    #                     'account_id': 360,  # Revenue account
    #                 }),
    #                 (0, 0, {
    #                     'name': "Advance Adjustment",
    #                     'quantity': 1.0,
    #                     'price_unit': -advance_charge,
    #                     'account_id': 360,  # Same revenue account (for adjustments)
    #                 }),
    #             ],
    #         }

    #         final_invoice = self.env['account.move'].create(final_invoice_vals)
    #         record.request_line_id.write({
    #             'final_invoice_id': final_invoice.id,
    #             # 'payment_state': 'full',
    #         }) 
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'reload',
    #         'params': {'action': 'reload_page'},
    #     }
     
    def action_start_trip(self):
        """Action method to set the order state to 'in_transit' with Nepali datetime."""
        kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        # print("timezone", kathmandu_tz)
        now_nep = datetime.now(kathmandu_tz)
        # print("now_nep", now_nep)
        # Format time to HH:MM:SS (dropping microseconds)
        self.pickup_time = now_nep.strftime("%H:%M:%S")
        # print("pickup_time", self.pickup_time)
        # Set the scheduled_date_from to today's date
        self.scheduled_date_from = fields.Date.today()
        # print("scheduled_date_from", self.scheduled_date_from)
        self.state = 'in_transit'
        return self._reload_action()

    def action_generate_invoice(self):
        # """Action method to set the order state to 'delivered' with Nepali datetime."""
        # kathmandu_tz = pytz.timezone('Asia/Kathmandu')
        # # print("timezone", kathmandu_tz)
        # now_nep = datetime.now(kathmandu_tz)
        # # print("now_nep", now_nep)
        # self.delivery_time = now_nep.strftime("%H:%M:%S")
        # # print("delivery_time", self.delivery_time)
        # # Set the scheduled_date_to to today's date
        # self.scheduled_date_to = fields.Date.today()
        # # print("scheduled_date_to", self.scheduled_date_to)
        # self.state = 'delivered'
        for record in self:
            partner = self.env['res.partner'].search([('name', '=', record.customer_name.name)], limit=1)
        # Prepare invoice values for service charge
            invoice_vals = {
                'move_type': 'out_invoice',  # 'out_invoice' for customer invoice
                'partner_id':partner.id,
                'invoice_date': fields.Date.today(), 
                'invoice_date_due':fields.Date.today() + timedelta(days=7),# Invoice date (can be dynamic)
                'invoice_line_ids': [
                    (0, 0, {
                        'name': "Transport Charge",
                        'currency_id': 117,# Service description
                        'quantity': 1.0,  # Fixed quantity for a service
                        'price_unit': record.total_service_charge,  # Service charge amount
                        'account_id': 360,  # Revenue account
                        # 'tax_ids':117,  # Applicable taxes (if any)
                    }),
                ],
            }

            # Create the service invoice
            invoice = self.env['account.move'].create(invoice_vals)
            if invoice:
                print("Invoice ",invoice.id)
            # Optional: Post the invoice to make it official
            # invoice.action_post()
            # record.request_id.state = 'delivered'
            record.request_line_id.state = 'delivered'
            # Return the invoice object for reference
        return self._reload_action()

    def action_search_related_model(self):
        wizard = self.env['route.search.wizard'].create({
            'pickup_date':self.scheduled_date_from,
            'delivery_date':self.scheduled_date_to, #weight
            'destination': self.delivery_address,
            'source': self.pickup_address,
            'weight':self.cargo_weight,
            'main_id': self.id,
        })
        wizard.populate_routes()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'route.search.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
    def action_print_invoice(self):
        invoice = self.env['customer.request.line'].search([('line_id.id' , '=' ,self.request_id.id )],limit=1)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context' :{
                'default_invoice_id':invoice.invoice_id.id,
                'default_action_domain': 'transport_invoice',
            }
        }
    def cancel_order(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context':{
                'active_id': self.id,
            }
        }

# class DeliveryDetails(models.Model):
#     _name = 'delivery.details'
#     _description = 'Delivery Details'

#     request_id = fields.Many2one('customer.request', string='Request ID')
#     proof_of_delivery = fields.Many2one('transport.pod', string='Proof of Delivery')
    