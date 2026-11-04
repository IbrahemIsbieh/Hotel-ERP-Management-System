from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HotelShift(models.Model):
    _name = 'hotel.shift'
    _description = 'Work Shift'
    _order = 'hotel_id, start_hour'

    name = fields.Char(required=True)
    hotel_id = fields.Many2one('hotel.hotel', required=True)
    start_hour = fields.Float(required=True, default=8.0)
    end_hour = fields.Float(required=True, default=16.0)
    duration = fields.Float('Duration (h)', compute='_compute_duration', store=True)
    color = fields.Integer()

    @api.depends('start_hour', 'end_hour')
    def _compute_duration(self):
        for shift in self:
            end = shift.end_hour
            if end <= shift.start_hour:  # overnight shift
                end += 24
            shift.duration = end - shift.start_hour

    @api.constrains('start_hour', 'end_hour')
    def _check_hours(self):
        for shift in self:
            if not (0 <= shift.start_hour < 24 and 0 <= shift.end_hour <= 24):
                raise ValidationError(self.env._('Shift hours must be between 00:00 and 24:00.'))
            if shift.start_hour == shift.end_hour:
                raise ValidationError(self.env._('A shift cannot start and end at the same time.'))