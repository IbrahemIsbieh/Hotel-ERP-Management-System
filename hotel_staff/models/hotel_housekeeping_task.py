from odoo import api, fields, models
from odoo.exceptions import UserError

ON_DUTY_STATES = ('planned', 'confirmed')


class HotelHousekeepingTask(models.Model):
    _inherit = 'hotel.housekeeping.task'

    assigned_employee_id = fields.Many2one(
        'hr.employee', compute='_compute_assigned_employee_id', store=True)
    assignee_on_shift = fields.Boolean(
        compute='_compute_assignee_on_shift', compute_sudo=True)

    @api.depends('assigned_user_id')
    def _compute_assigned_employee_id(self):
        for task in self:
            task.assigned_employee_id = task.assigned_user_id.employee_id

    @api.depends('assigned_employee_id', 'scheduled_date')
    def _compute_assignee_on_shift(self):
        for task in self:
            task.assignee_on_shift = bool(task.assigned_employee_id) and bool(
                self.env['hotel.shift.assignment'].search_count([
                    ('employee_id', '=', task.assigned_employee_id.id),
                    ('date', '=', task.scheduled_date),
                    ('state', 'in', ON_DUTY_STATES),
                ]))

    def action_auto_assign(self):
        Assignment = self.env['hotel.shift.assignment'].sudo()
        for task in self:
            employees = Assignment.search([
                ('hotel_id', '=', task.hotel_id.id),
                ('date', '=', task.scheduled_date),
                ('state', 'in', ON_DUTY_STATES),
                ('department', '=', 'housekeeping'),
                ('employee_id.user_id', '!=', False),
            ]).employee_id
            if not employees:
                raise UserError(self.env._(
                    'No housekeeping employee is on shift on %(d)s at %(h)s.',
                    d=task.scheduled_date, h=task.hotel_id.name))
            best = min(employees, key=lambda e: self.search_count([
                ('assigned_user_id', '=', e.user_id.id),
                ('state', 'in', ('pending', 'in_progress')),
            ]))
            task.assigned_user_id = best.user_id