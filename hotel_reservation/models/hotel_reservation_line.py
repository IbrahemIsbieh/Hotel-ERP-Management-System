from datetime import timedelta

from odoo import api, fields, models


class HotelReservationLine(models.Model):
    _name = 'hotel.reservation.line'
    _description = 'Reservation Room Line'

    reservation_id = fields.Many2one('hotel.reservation', required=True, ondelete='cascade')
    hotel_id = fields.Many2one(related='reservation_id.hotel_id', store=True)
    room_id = fields.Many2one('hotel.room', required=True)
    room_type_id = fields.Many2one(related='room_id.room_type_id')
    max_guests = fields.Integer(related='room_id.max_guests')
    currency_id = fields.Many2one(related='reservation_id.currency_id')
    price_total = fields.Monetary(compute='_compute_price_total', store=True)

    def _get_night_price(self, date):
        """Seasonal price of the room type for that night, else the room price."""
        self.ensure_one()
        room = self.room_id
        seasonal = self.env['hotel.season.price'].search([
            ('room_type_id', '=', room.room_type_id.id),
            ('season_id.hotel_id', '=', room.hotel_id.id),
            ('season_id.date_from', '<=', date),
            ('season_id.date_to', '>=', date),
        ], limit=1)
        return seasonal.price or room.price

    @api.depends('room_id', 'reservation_id.checkin_date', 'reservation_id.checkout_date')
    def _compute_price_total(self):
        for line in self:
            total = 0.0
            checkin = line.reservation_id.checkin_date
            checkout = line.reservation_id.checkout_date
            if line.room_id and checkin and checkout:
                for i in range((checkout - checkin).days):
                    total += line._get_night_price(checkin + timedelta(days=i))
            line.price_total = total

    @api.constrains('room_id')
    def _check_room_overlap(self):
        self.reservation_id._check_room_overlap()