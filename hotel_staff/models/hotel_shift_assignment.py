from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class HotelShiftAssignment(models.Model):
    _name = 'hotel.shift.assignment'
    _description = 'Shift Assignment'
    _inherit = ['mail.thread']
    _order = 'date desc, shift_id, employee_id'

    name = fields.Char(compute='_compute_name', store=True)
    hotel_id = fields.Many2one('hotel.hotel', required=True)
    employee_id = fields.Many2one(
        'hr.employee', required=True, tracking=True,
        domain="[('hotel_id', '=', hotel_id)]")
    department = fields.Selection(related='employee_id.hotel_department', store=True)
    shift_id = fields.Many2one(
        'hotel.shift', required=True, tracking=True,
        domain="[('hotel_id', '=', hotel_id)]")
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    state = fields.Selection([
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('absent', 'Absent'),
    ], default='planned', required=True, tracking=True)
    responsibilities = fields.Text(
        help='Tasks for this shift, e.g. floors 2-3, VIP arrivals, airport pickup.')

    _emp_date_shift_uniq = models.Constraint(
        'unique(employee_id, date, shift_id)',
        'This employee is already assigned to this shift on that day.')

    @api.depends('employee_id', 'shift_id', 'date')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s - %s' % (
                rec.employee_id.name or '', rec.shift_id.name or '', rec.date or '')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id.hotel_id:
            self.hotel_id = self.employee_id.hotel_id
        if self.employee_id.hotel_role_id and not self.responsibilities:
            self.responsibilities = self.employee_id.hotel_role_id.description

    # ---------- constraints ----------
    @api.constrains('employee_id', 'hotel_id', 'shift_id')
    def _check_hotel(self):
        for rec in self:
            if rec.employee_id.hotel_id and rec.employee_id.hotel_id != rec.hotel_id:
                raise ValidationError(self.env._(
                    '%(e)s works at another hotel.', e=rec.employee_id.name))
            if rec.shift_id.hotel_id != rec.hotel_id:
                raise ValidationError(self.env._('The shift belongs to a different hotel.'))

    def _get_interval(self):
        self.ensure_one()
        midnight = fields.Datetime.to_datetime(self.date)
        start_h = self.shift_id.start_hour
        end_h = self.shift_id.end_hour
        if end_h <= start_h:
            end_h += 24
        return midnight + timedelta(hours=start_h), midnight + timedelta(hours=end_h)

    @api.constrains('employee_id', 'date', 'shift_id', 'state')
    def _check_overlap(self):
        for rec in self.filtered(lambda r: r.state != 'absent'):
            start, end = rec._get_interval()
            neighbours = self.search([
                ('id', '!=', rec.id),
                ('employee_id', '=', rec.employee_id.id),
                ('state', '!=', 'absent'),
                ('date', '>=', rec.date - timedelta(days=1)),
                ('date', '<=', rec.date + timedelta(days=1)),
            ])
            for other in neighbours:
                o_start, o_end = other._get_interval()
                if o_start < end and o_end > start:
                    raise ValidationError(self.env._(
                        '%(e)s already has an overlapping shift: %(o)s',
                        e=rec.employee_id.name, o=other.name))

    # ---------- workflow ----------
    def action_confirm(self):
        self.filtered(lambda r: r.state == 'planned').write({'state': 'confirmed'})

    def action_done(self):
        self.filtered(lambda r: r.state == 'confirmed').write({'state': 'done'})

    def action_absent(self):
        self.filtered(lambda r: r.state in ('planned', 'confirmed')).write({'state': 'absent'})

    def action_reset(self):
        self.filtered(lambda r: r.state in ('absent', 'confirmed')).write({'state': 'planned'})