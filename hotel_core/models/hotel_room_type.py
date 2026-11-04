from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HotelRoomType(models.Model):
    _name = 'hotel.room.type'
    _description = 'Room Type'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    image = fields.Image(max_width=1024, max_height=1024)
    description = fields.Html()
    max_adults = fields.Integer(default=2)
    max_children = fields.Integer(default=0)
    max_guests = fields.Integer(compute='_compute_max_guests', store=True)
    base_price = fields.Monetary(currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    amenity_ids = fields.Many2many('hotel.amenity')
    room_ids = fields.One2many('hotel.room', 'room_type_id')
    room_count = fields.Integer(compute='_compute_room_count')

    _code_uniq = models.Constraint('unique(code)', 'Room type code must be unique.')

    @api.depends('max_adults', 'max_children')
    def _compute_max_guests(self):
        for rec in self:
            rec.max_guests = rec.max_adults + rec.max_children

    @api.depends('room_ids')
    def _compute_room_count(self):
        for rec in self:
            rec.room_count = len(rec.room_ids)

    @api.constrains('max_adults', 'base_price')
    def _check_values(self):
        for rec in self:
            if rec.max_adults < 1:
                raise ValidationError(self.env._('A room must host at least one adult.'))
            if rec.base_price < 0:
                raise ValidationError(self.env._('Base price cannot be negative.'))