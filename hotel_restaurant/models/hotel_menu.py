from odoo import fields, models


class HotelMenuCategory(models.Model):
    _name = 'hotel.menu.category'
    _description = 'Menu Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)


class HotelMenuItem(models.Model):
    _name = 'hotel.menu.item'
    _description = 'Menu Item'
    _order = 'category_id, name'

    name = fields.Char(required=True, translate=True)
    category_id = fields.Many2one('hotel.menu.category')
    image = fields.Image(max_width=512, max_height=512)
    price = fields.Monetary(currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    available = fields.Boolean(default=True)
    description = fields.Text()
    restaurant_ids = fields.Many2many(
        'hotel.restaurant', 'hotel_menu_item_restaurant_rel',
        'item_id', 'restaurant_id', string='Served In')