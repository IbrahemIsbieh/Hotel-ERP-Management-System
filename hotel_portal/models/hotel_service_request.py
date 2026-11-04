from odoo import api, fields, models
from odoo.exceptions import UserError


class HotelServiceRequest(models.Model):
    _name = 'hotel.service.request'
    _description = 'Guest Service Request'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(default='New', readonly=True, copy=False)
    reservation_id = fields.Many2one(
        'hotel.reservation', required=True, ondelete='cascade', tracking=True)
    partner_id = fields.Many2one(related='reservation_id.partner_id', store=True)
    hotel_id = fields.Many2one(related='reservation_id.hotel_id', store=True)
    request_type = fields.Selection([
        ('housekeeping', 'Extra Cleaning'),
        ('amenities', 'Extra Towels / Amenities'),
        ('early_checkin', 'Early Check-in'),
        ('late_checkout', 'Late Check-out'),
        ('maintenance', 'Maintenance'),
        ('transport', 'Airport Transfer'),
        ('other', 'Other'),
    ], default='other', required=True)
    description = fields.Text(required=True)
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], default='new', required=True, tracking=True, copy=False)
    assigned_user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)
    response = fields.Text(help='Visible to the guest when the request is closed.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hotel.service.request') or 'New'
        records = super().create(vals_list)
        for rec in records:
            rec.message_subscribe(partner_ids=rec.partner_id.ids)
        return records

    def action_start(self):
        self.filtered(lambda r: r.state == 'new').write({
            'state': 'in_progress',
            'assigned_user_id': self.env.user.id,
        })

    def _notify_guest(self, body):
        for rec in self:
            rec.message_post(
                body=body, message_type='comment', subtype_xmlid='mail.mt_comment',
                partner_ids=rec.partner_id.ids)

    def action_done(self):
        for rec in self.filtered(lambda r: r.state in ('new', 'in_progress')):
            rec.state = 'done'
            rec._notify_guest(rec.response or self.env._('Your request has been completed.'))

    def action_reject(self):
        for rec in self.filtered(lambda r: r.state in ('new', 'in_progress')):
            if not rec.response:
                raise UserError(self.env._('Write a response explaining the rejection first.'))
            rec.state = 'rejected'
            rec._notify_guest(rec.response)