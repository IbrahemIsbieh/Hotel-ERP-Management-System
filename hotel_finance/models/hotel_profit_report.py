from odoo import fields, models


class HotelProfitReport(models.Model):
    _name = 'hotel.profit.report'
    _description = 'Hotel Revenue & Expense Report'
    _auto = False
    _order = 'date desc'

    hotel_id = fields.Many2one('hotel.hotel', readonly=True)
    date = fields.Date(readonly=True)
    line_type = fields.Selection([
        ('room', 'Room Revenue'),
        ('services', 'Extra Charges Revenue'),
        ('restaurant', 'Restaurant Revenue'),
        ('expense', 'Expense'),
    ], readonly=True)
    category = fields.Char(readonly=True)
    amount = fields.Float(readonly=True)
    signed_amount = fields.Float('Profit Impact', readonly=True)

    def init(self):
        self.env.cr.execute(f"DROP VIEW IF EXISTS {self._table} CASCADE")
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    q.hotel_id,
                    q.date,
                    q.line_type,
                    q.category,
                    q.amount,
                    CASE WHEN q.line_type = 'expense' THEN -q.amount ELSE q.amount END
                        AS signed_amount
                FROM (
                    SELECT r.hotel_id, r.checkout_date AS date,
                           'room'::varchar AS line_type,
                           'Rooms'::varchar AS category,
                           r.amount_total AS amount
                      FROM hotel_reservation r
                     WHERE r.state = 'checked_out'
                    UNION ALL
                    SELECT r.hotel_id, r.checkout_date, 'services', 'Extra charges',
                           r.charges_total
                      FROM hotel_reservation r
                     WHERE r.state = 'checked_out' AND r.charges_total > 0
                    UNION ALL
                    SELECT o.hotel_id, o.date::date, 'restaurant', 'Restaurant',
                           o.amount_total
                      FROM hotel_restaurant_order o
                     WHERE o.state = 'billed' AND o.payment_method IN ('cash', 'card')
                    UNION ALL
                    SELECT e.hotel_id, e.date, 'expense', e.category, e.amount
                      FROM hotel_expense e
                     WHERE e.state IN ('approved', 'paid')
                ) q
            )
        """)