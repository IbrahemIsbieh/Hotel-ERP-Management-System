from odoo import fields, models


class HotelRestaurant(models.Model):
    _name = 'hotel.restaurant'
    _description = 'Hotel Restaurant / Outlet'

    name = fields.Char(required=True)
    hotel_id = fields.Many2one('hotel.hotel', required=True)
    restaurant_type = fields.Selection([
        ('restaurant', 'Restaurant'),
        ('cafe', 'Cafe'),
        ('bar', 'Bar'),
        ('room_service', 'Room Service'),
    ], default='restaurant', required=True)
    opening_time = fields.Float(default=7.0)
    closing_time = fields.Float(default=23.0)
    service_charge_pct = fields.Float('Service Charge (%)', default=0.0)
    active = fields.Boolean(default=True)
    item_ids = fields.Many2many(
        'hotel.menu.item', 'hotel_menu_item_restaurant_rel',
        'restaurant_id', 'item_id', string='Menu')
    company_id = fields.Many2one(related='hotel_id.company_id', store=True)