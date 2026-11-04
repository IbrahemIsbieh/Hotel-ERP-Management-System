from odoo import fields, models


class HotelBuilding(models.Model):
    _name = 'hotel.building'
    _description = 'Hotel Building'

    name = fields.Char(required=True)
    hotel_id = fields.Many2one('hotel.hotel', required=True, ondelete='cascade')
    floor_ids = fields.One2many('hotel.floor', 'building_id')
    notes = fields.Text()