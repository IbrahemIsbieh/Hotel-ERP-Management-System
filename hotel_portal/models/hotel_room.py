from datetime import timedelta

from odoo import models


class HotelRoom(models.Model):
    _inherit = 'hotel.room'

    def _get_stay_price(self, checkin, checkout):
        """Total price: seasonal price per night, else the room price."""
        self.ensure_one()
        SeasonPrice = self.env['hotel.season.price']
        total = 0.0
        for i in range((checkout - checkin).days):
            day = checkin + timedelta(days=i)
            seasonal = SeasonPrice.search([
                ('room_type_id', '=', self.room_type_id.id),
                ('season_id.hotel_id', '=', self.hotel_id.id),
                ('season_id.date_from', '<=', day),
                ('season_id.date_to', '>=', day),
            ], limit=1)
            total += seasonal.price or self.price
        return total