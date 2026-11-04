from odoo import fields, models


class HotelFloor(models.Model):
    _name = 'hotel.floor'
    _description = 'Hotel Floor'
    _order = 'building_id, number'

    name = fields.Char(required=True)
    number = fields.Integer(required=True)
    building_id = fields.Many2one('hotel.building', required=True, ondelete='cascade')
    hotel_id = fields.Many2one(related='building_id.hotel_id', store=True)
    room_ids = fields.One2many('hotel.room', 'floor_id')

    _number_uniq = models.Constraint(
        'unique(building_id, number)', 'Floor number must be unique per building.')