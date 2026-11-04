from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

ACTIVE_STATES = ('confirmed', 'checked_in')


class HotelReservation(models.Model):
    _name = 'hotel.reservation'
    _description = 'Hotel Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'checkin_date desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False)
    hotel_id = fields.Many2one('hotel.hotel', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Guest', required=True, tracking=True)
    checkin_date = fields.Date(
        required=True, default=fields.Date.context_today, tracking=True)
    checkout_date = fields.Date(
        required=True, tracking=True,
        default=lambda self: fields.Date.context_today(self) + timedelta(days=1))
    nights = fields.Integer(compute='_compute_nights', store=True)
    adults = fields.Integer(default=1)
    children = fields.Integer(default=0)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True, copy=False)

    line_ids = fields.One2many('hotel.reservation.line', 'reservation_id', copy=True)
    available_room_ids = fields.Many2many('hotel.room', compute='_compute_available_room_ids')
    company_id = fields.Many2one(related='hotel_id.company_id', store=True)
    currency_id = fields.Many2one(related='hotel_id.currency_id')
    amount_total = fields.Monetary(compute='_compute_amount_total', store=True)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.reservation') or 'New'
        return super().create(vals_list)

    # ---------- computes ----------
    @api.depends('checkin_date', 'checkout_date')
    def _compute_nights(self):
        for rec in self:
            if rec.checkin_date and rec.checkout_date:
                rec.nights = (rec.checkout_date - rec.checkin_date).days
            else:
                rec.nights = 0

    @api.depends('line_ids.price_total')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped('price_total'))

    @api.depends('hotel_id', 'checkin_date', 'checkout_date')
    def _compute_available_room_ids(self):
        for rec in self:
            rec.available_room_ids = rec._get_available_rooms()

    def _get_available_rooms(self):
        """Rooms of the hotel not booked by another active reservation
        overlapping the dates of this reservation."""
        self.ensure_one()
        if not (self.hotel_id and self.checkin_date and self.checkout_date):
            return self.env['hotel.room']
        rooms = self.env['hotel.room'].search([
            ('hotel_id', '=', self.hotel_id.id),
            ('state', '!=', 'out_of_service'),
        ])
        busy = self.env['hotel.reservation.line'].search([
            ('reservation_id', '!=', self._origin.id),
            ('reservation_id.state', 'in', ACTIVE_STATES),
            ('reservation_id.checkin_date', '<', self.checkout_date),
            ('reservation_id.checkout_date', '>', self.checkin_date),
        ]).room_id
        return rooms - busy

    # ---------- constraints ----------
    @api.constrains('checkin_date', 'checkout_date')
    def _check_dates(self):
        for rec in self:
            if rec.checkout_date <= rec.checkin_date:
                raise ValidationError(self.env._('Check-out must be after check-in.'))

    @api.constrains('adults', 'children')
    def _check_guests(self):
        for rec in self:
            if rec.adults < 1 or rec.children < 0:
                raise ValidationError(self.env._('At least one adult is required.'))

    @api.constrains('state', 'checkin_date', 'checkout_date', 'line_ids')
    def _check_room_overlap(self):
        Line = self.env['hotel.reservation.line']
        for rec in self.filtered(lambda r: r.state in ACTIVE_STATES):
            for line in rec.line_ids:
                clash = Line.search([
                    ('id', '!=', line.id),
                    ('room_id', '=', line.room_id.id),
                    ('reservation_id.state', 'in', ACTIVE_STATES),
                    ('reservation_id.checkin_date', '<', rec.checkout_date),
                    ('reservation_id.checkout_date', '>', rec.checkin_date),
                ], limit=1)
                if clash:
                    raise ValidationError(self.env._(
                        'Room %(room)s is already booked in these dates (%(rsv)s).',
                        room=line.room_id.name, rsv=clash.reservation_id.name))

    # ---------- actions ----------
    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(self.env._('Add at least one room before confirming.'))
            capacity = sum(rec.line_ids.mapped('room_id.max_guests'))
            if rec.adults + rec.children > capacity:
                raise UserError(self.env._(
                    'Guests (%(g)s) exceed the capacity of the selected rooms (%(c)s).',
                    g=rec.adults + rec.children, c=capacity))
            rec.line_ids._compute_price_total()
            rec.state = 'confirmed'

    def action_cancel(self):
        for rec in self:
            if rec.state in ('checked_in', 'checked_out'):
                raise UserError(self.env._('You cannot cancel a reservation after check-in.'))
        self.state = 'cancelled'

    def action_draft(self):
        self.filtered(lambda r: r.state == 'cancelled').state = 'draft'