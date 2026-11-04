from odoo import fields, models


class HotelHousekeepingItem(models.Model):
    _name = 'hotel.housekeeping.item'
    _description = 'Housekeeping Checklist Template Item'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)