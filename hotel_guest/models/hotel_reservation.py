from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class HotelReservation(models.Model):
    _inherit = 'hotel.reservation'

    companion_ids = fields.One2many('hotel.reservation.companion', 'reservation_id', copy=True)
    guest_vip = fields.Selection(related='partner_id.guest_vip')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.partner_id.filtered(lambda p: not p.is_guest).is_guest = True
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'partner_id' in vals:
            self.partner_id.filtered(lambda p: not p.is_guest).is_guest = True
        return res

    @api.constrains('companion_ids', 'adults', 'children')
    def _check_companions(self):
        for rec in self:
            if len(rec.companion_ids) > rec.adults + rec.children - 1:
                raise ValidationError(self.env._(
                    'Companions cannot exceed the total number of guests minus the main guest.'))

    def action_confirm(self):
        for rec in self:
            if rec.partner_id.guest_blacklisted:
                raise UserError(self.env._(
                    'Guest %(name)s is blacklisted: %(reason)s',
                    name=rec.partner_id.name,
                    reason=rec.partner_id.guest_blacklist_reason or '-'))
        return super().action_confirm()