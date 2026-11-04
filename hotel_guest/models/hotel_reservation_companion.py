from odoo import fields, models

from .res_partner import ID_TYPES


class HotelReservationCompanion(models.Model):
    _name = 'hotel.reservation.companion'
    _description = 'Reservation Companion'

    reservation_id = fields.Many2one('hotel.reservation', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')])
    nationality_id = fields.Many2one('res.country')
    id_type = fields.Selection(ID_TYPES)
    id_number = fields.Char()
    is_child = fields.Boolean()