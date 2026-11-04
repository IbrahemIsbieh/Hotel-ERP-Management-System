from odoo import fields, models

from .hotel_staff_role import DEPARTMENTS


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hotel_id = fields.Many2one('hotel.hotel', string='Hotel', tracking=True)
    hotel_department = fields.Selection(DEPARTMENTS, string='Hotel Department', tracking=True)
    hotel_role_id = fields.Many2one(
        'hotel.staff.role', string='Hotel Role',
        domain="[('department', '=', hotel_department)]")
    shift_assignment_ids = fields.One2many('hotel.shift.assignment', 'employee_id')
    shift_count = fields.Integer(compute='_compute_shift_count')

    def _compute_shift_count(self):
        data = self.env['hotel.shift.assignment']._read_group(
            [('employee_id', 'in', self.ids)], ['employee_id'], ['__count'])
        counts = {employee.id: count for employee, count in data}
        for emp in self:
            emp.shift_count = counts.get(emp.id, 0)

    def action_view_shifts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Shifts'),
            'res_model': 'hotel.shift.assignment',
            'view_mode': 'list,calendar,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id,
                        'default_hotel_id': self.hotel_id.id},
        }