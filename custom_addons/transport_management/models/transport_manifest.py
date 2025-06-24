# models/transport_manifest.py
from odoo import models, fields, api
from ..models.transport_order import convert_to_bs_date

class TransportManifest(models.Model):
    _name = 'transport.manifest'
    _description = 'Transport Manifest'
    _order = 'create_date desc'
    _rec_name = 'code'

    # Unique code for the manifest
    code = fields.Char(
        string='Manifest Code',
        copy=False,
        readonly=True,
        default='New'
    )

    # Link to the parent Transport Order
    order_id = fields.Many2one(
        'transport.order', string='Order Id', required=True, ondelete='cascade'
    )

    # Optional link to assignment (if needed)
    assignment_id = fields.Many2one(
        'transport.assignment', string='Assignment'
    )

    # One2many relationship to Manifest Lines
    line_ids = fields.One2many(
        'transport.manifest.line', 'manifest_id', string='Manifest Lines'
    )

    # Date when the manifest was generated
    generated_date = fields.Date(
        string='Generated Date', default=fields.Date.today, required=True
    )

    # BS (Nepali date) version of generated date (computed)
    generated_date_bs = fields.Char(
        string='Generated Date BS', compute='_compute_date_bs'
    )

    # Optional binary attachment, e.g., PDF copy of the manifest
    attachment_id = fields.Binary(string='PDF/Attachment')

    @api.depends('generated_date')
    def _compute_date_bs(self):
        """
        Compute the BS (Nepali) date equivalent for the generated date
        using the shared utility function.
        """
        for record in self:
            record.generated_date_bs = convert_to_bs_date(record.generated_date) if record.generated_date else False

    def _generate_manifest_code(self):
        """
        Generate a unique manifest code in the format 'Manifest/NNN'
        by finding the last created manifest record and incrementing its number.
        """
        last_manifest = self.search([], order='id desc', limit=1)
        if last_manifest and last_manifest.code:
            try:
                # Extract the numerical part from the format "Manifest/001"
                last_number = int(last_manifest.code.split('/')[-1])
                next_number = last_number + 1
            except Exception:
                next_number = 1
        else:
            next_number = 1
        # Format the new code with leading zeros, e.g., Manifest/001
        return "Manifest/%05d" % next_number

    @api.model
    def create(self, vals):
        # Generate a unique code if the code field is 'New'
        if vals.get('code', 'New') == 'New':
            vals['code'] = self._generate_manifest_code()
        return super(TransportManifest, self).create(vals)

class TransportManifestLine(models.Model):
    _name = 'transport.manifest.line'
    _description = 'Transport Manifest Line'
    _order = 'create_date desc'

    # Link back to the parent Manifest
    manifest_id = fields.Many2one(
        'transport.manifest', string='Manifest', required=True, ondelete='cascade'
    )

    # Sequence of the stop within the manifest
    sequence = fields.Integer(string='Stop Sequence', default=1)

    # Description of the cargo or stop
    description = fields.Char(string='Description')

    # Cargo weight at this stop
    cargo_weight = fields.Float(string='Weight (kg)')

    # Cargo quantity at this stop
    cargo_qty = fields.Integer(string='Quantity')

    # Cargo type at this stop
    cargo_type = fields.Char(string='Cargo Type')

    # Estimated Time of Arrival at the stop (Gregorian)
    eta = fields.Date(string='ETA', help='Estimated Time of Arrival')

    # ETA in Nepali BS date format (computed)
    eta_bs = fields.Char(string='ETA BS', compute='_compute_date_bs')

    @api.depends('eta')
    def _compute_date_bs(self):
        """
        Compute the BS (Nepali) date equivalent for the ETA date.
        """
        for record in self:
            record.eta_bs = convert_to_bs_date(record.eta) if record.eta else False
