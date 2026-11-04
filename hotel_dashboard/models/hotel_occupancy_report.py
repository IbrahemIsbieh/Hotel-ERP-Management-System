from odoo import fields, models


class HotelOccupancyReport(models.Model):
    _name = 'hotel.occupancy.report'
    _description = 'Room Nights Report'
    _auto = False
    _order = 'date desc'

    hotel_id = fields.Many2one('hotel.hotel', readonly=True)
    date = fields.Date('Night', readonly=True)
    room_id = fields.Many2one('hotel.room', readonly=True)
    room_type_id = fields.Many2one('hotel.room.type', readonly=True)
    reservation_id = fields.Many2one('hotel.reservation', readonly=True)
    state = fields.Selection([
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
    ], readonly=True)
    room_nights = fields.Integer(readonly=True)
    night_rate = fields.Float('Night Revenue', readonly=True)

    def init(self):
        self.env.cr.execute(f"DROP VIEW IF EXISTS {self._table} CASCADE")
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    r.hotel_id AS hotel_id,
                    d.night::date AS date,
                    l.room_id AS room_id,
                    rm.room_type_id AS room_type_id,
                    r.id AS reservation_id,
                    r.state AS state,
                    1 AS room_nights,
                    CASE WHEN r.checkout_date > r.checkin_date
                         THEN l.price_total::numeric
                              / (r.checkout_date - r.checkin_date)
                         ELSE 0 END AS night_rate
                FROM hotel_reservation_line l
                JOIN hotel_reservation r ON r.id = l.reservation_id
                JOIN hotel_room rm ON rm.id = l.room_id
                CROSS JOIN LATERAL generate_series(
                    r.checkin_date::timestamp,
                    (r.checkout_date - 1)::timestamp,
                    interval '1 day') AS d(night)
                WHERE r.state IN ('confirmed', 'checked_in', 'checked_out')
            )
        """)