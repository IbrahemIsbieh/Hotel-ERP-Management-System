from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError

OPEN_STATES = ('pending', 'in_progress', 'done')


class HotelHousekeepingTask(models.Model):
    _name = 'hotel.housekeeping.task'
    _description = 'Housekeeping Task'
    _inherit = ['mail.thread']
    _order = 'priority desc, scheduled_date, id'

    name = fields.Char(default='New', readonly=True, copy=False)
    room_id = fields.Many2one('hotel.room', required=True, tracking=True)
    hotel_id = fields.Many2one(related='room_id.hotel_id', store=True)
    floor_id = fields.Many2one(related='room_id.floor_id', store=True)
    room_type_id = fields.Many2one(related='room_id.room_type_id')
    company_id = fields.Many2one(related='hotel_id.company_id', store=True)

    task_type = fields.Selection([
        ('checkout', 'Check-out Cleaning'),
        ('daily', 'Daily Cleaning'),
        ('deep', 'Deep Cleaning'),
    ], default='checkout', required=True)
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], default='0',
        help='Urgent: a guest is arriving in this room today.')
    scheduled_date = fields.Date(default=fields.Date.context_today, required=True)
    assigned_user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)

    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('inspected', 'Inspected'),
        ('cancelled', 'Cancelled'),
    ], default='pending', required=True, tracking=True, copy=False)

    start_time = fields.Datetime(readonly=True, copy=False)
    end_time = fields.Datetime(readonly=True, copy=False)
    duration = fields.Float('Duration (min)', compute='_compute_duration', store=True)
    inspected_by_id = fields.Many2one('res.users', readonly=True, copy=False)
    inspected_on = fields.Datetime(readonly=True, copy=False)

    line_ids = fields.One2many('hotel.housekeeping.task.line', 'task_id', copy=True)
    progress = fields.Float(compute='_compute_progress')
    notes = fields.Text()

    # ---------- create ----------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hotel.housekeeping.task') or 'New'
        tasks = super().create(vals_list)
        items = self.env['hotel.housekeeping.item'].search([])
        for task in tasks.filtered(lambda t: not t.line_ids):
            task.line_ids = [
                Command.create({'name': item.name, 'sequence': item.sequence})
                for item in items
            ]
        return tasks

    @api.model
    def _get_priority_for_room(self, room):
        today = fields.Date.context_today(self)
        arriving = self.env['hotel.reservation.line'].sudo().search_count([
            ('room_id', '=', room.id),
            ('reservation_id.state', '=', 'confirmed'),
            ('reservation_id.checkin_date', '<=', today),
        ])
        return '1' if arriving else '0'

    # ---------- computes ----------
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for task in self:
            if task.start_time and task.end_time:
                task.duration = (task.end_time - task.start_time).total_seconds() / 60.0
            else:
                task.duration = 0.0

    @api.depends('line_ids.done')
    def _compute_progress(self):
        for task in self:
            total = len(task.line_ids)
            task.progress = (len(task.line_ids.filtered('done')) / total * 100.0) if total else 0.0

    # ---------- workflow ----------
    def action_start(self):
        for task in self:
            if task.state != 'pending':
                raise UserError(self.env._('Only pending tasks can be started.'))
            task.write({
                'state': 'in_progress',
                'start_time': fields.Datetime.now(),
                'assigned_user_id': task.assigned_user_id.id or self.env.user.id,
            })

    def action_done(self):
        for task in self:
            if task.state != 'in_progress':
                raise UserError(self.env._('Start the task first.'))
            if task.line_ids.filtered(lambda l: not l.done):
                raise UserError(self.env._('Complete all checklist items before finishing.'))
            task.write({'state': 'done', 'end_time': fields.Datetime.now()})

    def action_inspect(self):
        for task in self:
            if task.state != 'done':
                raise UserError(self.env._('Only finished tasks can be inspected.'))
            task.write({
                'state': 'inspected',
                'inspected_by_id': self.env.user.id,
                'inspected_on': fields.Datetime.now(),
            })
            if task.room_id.state == 'cleaning':
                task.room_id.write({'state': 'available'})

    def action_cancel(self):
        for task in self:
            if task.state not in ('pending', 'in_progress'):
                raise UserError(self.env._('Only pending or in-progress tasks can be cancelled.'))
        self.write({'state': 'cancelled'})

    # ---------- cron ----------
    @api.model
    def _cron_generate_daily_tasks(self):
        today = fields.Date.context_today(self)
        rooms = self.env['hotel.room'].search([('state', '=', 'occupied')])
        for room in rooms:
            exists = self.search_count([
                ('room_id', '=', room.id),
                ('state', 'in', OPEN_STATES),
            ]) or self.search_count([
                ('room_id', '=', room.id),
                ('task_type', '=', 'daily'),
                ('scheduled_date', '=', today),
            ])
            if not exists:
                self.create({'room_id': room.id, 'task_type': 'daily'})


class HotelHousekeepingTaskLine(models.Model):
    _name = 'hotel.housekeeping.task.line'
    _description = 'Housekeeping Task Checklist Line'
    _order = 'sequence, id'

    task_id = fields.Many2one('hotel.housekeeping.task', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    done = fields.Boolean()