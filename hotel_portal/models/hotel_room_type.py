from odoo import fields, models


class HotelRoomType(models.Model):
    _inherit = 'hotel.room.type'

    portal_visible = fields.Boolean('Show Online', default=True)