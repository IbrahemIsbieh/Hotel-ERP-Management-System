from odoo import fields, models


class HotelHotel(models.Model):
    _inherit = 'hotel.hotel'

    portal_bookable = fields.Boolean('Bookable Online', default=True)
    portal_auto_confirm = fields.Boolean(
        'Auto-confirm Online Bookings', default=True,
        help='If disabled, online bookings stay in draft until the staff confirms them '
             '(a draft does NOT block the room).')
    portal_cancel_days = fields.Integer(
        'Free Cancellation (days before arrival)', default=1,
        help='Guests can cancel online only if arrival is at least this many days away.')
    portal_max_nights = fields.Integer('Max Nights per Online Booking', default=30)

    def _portal_get_available_rooms(self, checkin, checkout):
        self.ensure_one()
        rooms = self.env['hotel.room'].search([
            ('hotel_id', '=', self.id),
            ('state', '!=', 'out_of_service'),
        ])
        busy = self.env['hotel.reservation.line'].search([
            ('hotel_id', '=', self.id),
            ('reservation_id.state', 'in', ('confirmed', 'checked_in')),
            ('reservation_id.checkin_date', '<', checkout),
            ('reservation_id.checkout_date', '>', checkin),
        ]).room_id
        return rooms - busy

    def _portal_pick_room(self, room_type, checkin, checkout):
        """Cheapest available room of the type (same one is priced and booked)."""
        self.ensure_one()
        rooms = self._portal_get_available_rooms(checkin, checkout).filtered(
            lambda r: r.room_type_id == room_type)
        return rooms.sorted(lambda r: (r._get_stay_price(checkin, checkout), r.name))[:1]