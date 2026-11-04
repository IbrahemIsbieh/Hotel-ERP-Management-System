from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


class HotelShiftGenerateWizard(models.TransientModel):
    _name = 'hotel.shift.generate.wizard'
    _description = 'Generate Shift Schedule'

    hotel_id = fields.Many2one('hotel.hotel', required=True)
    shift_id = fields.Many2one(
        'hotel.shift', required=True, domain="[('hotel_id', '=', hotel_id)]")
    employee_ids = fields.Many2many(
        'hr.employee', required=True, domain="[('hotel_id', '=', hotel_id)]")
    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(
        required=True,
        default=lambda self: fields.Date.context_today(self) + timedelta(days=6))
    mon = fields.Boolean('Monday', default=True)
    tue = fields.Boolean('Tuesday', default=True)
    wed = fields.Boolean('Wednesday', default=True)
    thu = fields.Boolean('Thursday', default=True)
    fri = fields.Boolean('Friday', default=True)
    sat = fields.Boolean('Saturday', default=True)
    sun = fields.Boolean('Sunday', default=True)
    responsibilities = fields.Text()

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wiz in self:
            if wiz.date_to < wiz.date_from:
                raise ValidationError(self.env._('The end date must be after the start date.'))

    def action_generate(self):
        self.ensure_one()
        days = {i for i, f in enumerate(WEEKDAYS) if self[f]}
        if not days:
            raise UserError(self.env._('Select at least one weekday.'))
        Assignment = self.env['hotel.shift.assignment']
        created = skipped = 0
        for employee in self.employee_ids:
            day = self.date_from
            while day <= self.date_to:
                if day.weekday() in days:
                    try:
                        with self.env.cr.savepoint():
                            Assignment.create({
                                'hotel_id': self.hotel_id.id,
                                'employee_id': employee.id,
                                'shift_id': self.shift_id.id,
                                'date': day,
                                'responsibilities': self.responsibilities,
                            })
                        created += 1
                    except Exception:  # duplicate / overlap: skip silently
                        skipped += 1
                day += timedelta(days=1)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._('Schedule generated'),
                'message': self.env._(
                    '%(c)s assignment(s) created, %(s)s skipped (duplicates or overlaps).',
                    c=created, s=skipped),
                'type': 'success' if created else 'warning',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }