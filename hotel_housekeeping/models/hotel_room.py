from odoo import api, fields, models
from odoo.exceptions import UserError

from .hotel_housekeeping_task import OPEN_STATES


class HotelRoom(models.Model):
    _inherit = 'hotel.room'

    task_ids = fields.One2many('hotel.housekeeping.task', 'room_id')
    open_task_count = fields.Integer(compute='_compute_open_task_count')

    @api.depends('task_ids.state')
    def _compute_open_task_count(self):
        for room in self:
            room.open_task_count = len(room.task_ids.filtered(lambda t: t.state in OPEN_STATES))

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'cleaning':
            self._create_housekeeping_tasks()
        return res

    def _create_housekeeping_tasks(self):
        Task = self.env['hotel.housekeeping.task']
        for room in self:
            if Task.search_count([('room_id', '=', room.id), ('state', 'in', OPEN_STATES)]):
                continue
            Task.create({
                'room_id': room.id,
                'task_type': 'checkout',
                'priority': Task._get_priority_for_room(room),
            })

    def action_request_cleaning(self):
        if self.filtered(lambda r: r.state == 'occupied'):
            raise UserError(self.env._('An occupied room cannot be sent to cleaning.'))
        self.write({'state': 'cleaning'})

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Housekeeping Tasks'),
            'res_model': 'hotel.housekeeping.task',
            'view_mode': 'list,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }