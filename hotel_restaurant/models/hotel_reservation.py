from odoo import api, fields, models


class HotelReservation(models.Model):
    _inherit = 'hotel.reservation'

    restaurant_order_ids = fields.One2many('hotel.restaurant.order', 'reservation_id')
    restaurant_order_count = fields.Integer(compute='_compute_restaurant_order_count')

    @api.depends('restaurant_order_ids')
    def _compute_restaurant_order_count(self):
        for rec in self:
            rec.restaurant_order_count = len(rec.restaurant_order_ids)

    def action_view_restaurant_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Restaurant Orders'),
            'res_model': 'hotel.restaurant.order',
            'view_mode': 'list,form',
            'domain': [('reservation_id', '=', self.id)],
            'context': {'default_reservation_id': self.id,
                        'default_hotel_id': self.hotel_id.id},
        }