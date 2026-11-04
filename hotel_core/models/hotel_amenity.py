from odoo import fields, models


class HotelAmenity(models.Model):
    _name = 'hotel.amenity'
    _description = 'Room Amenity'

    name = fields.Char(required=True, translate=True)
    icon = fields.Char(help='Font Awesome class, e.g. fa-wifi')

    _name_uniq = models.Constraint('unique(name)', 'Amenity already exists.')