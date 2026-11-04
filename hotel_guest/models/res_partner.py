from odoo import api, fields, models
from odoo.exceptions import ValidationError

ID_TYPES = [
    ('national_id', 'National ID'),
    ('passport', 'Passport'),
    ('driving_license', 'Driving License'),
    ('other', 'Other'),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_guest = fields.Boolean(string='Hotel Guest')
    guest_gender = fields.Selection([('male', 'Male'), ('female', 'Female')])
    guest_birthdate = fields.Date(string='Date of Birth')
    guest_nationality_id = fields.Many2one('res.country', string='Nationality')
    guest_id_type = fields.Selection(ID_TYPES, string='ID Type')
    guest_id_number = fields.Char(string='ID Number')
    guest_vip = fields.Selection([
        ('regular', 'Regular'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ], string='VIP Level', default='regular')
    guest_preferences = fields.Text(
        string='Preferences', help='Pillow type, floor, allergies, special requests...')
    guest_blacklisted = fields.Boolean(string='Blacklisted', tracking=True)
    guest_blacklist_reason = fields.Text(string='Blacklist Reason')

    hotel_reservation_ids = fields.One2many('hotel.reservation', 'partner_id')
    guest_currency_id = fields.Many2one(
        'res.currency', compute='_compute_guest_currency')
    # compute_sudo: any internal user can open a partner form without
    # needing access rights on hotel models.
    guest_reservation_count = fields.Integer(
        compute='_compute_guest_stats', compute_sudo=True)
    guest_stay_count = fields.Integer(
        compute='_compute_guest_stats', compute_sudo=True)
    guest_total_spent = fields.Monetary(
        compute='_compute_guest_stats', compute_sudo=True,
        currency_field='guest_currency_id')
    guest_last_stay = fields.Date(
        compute='_compute_guest_stats', compute_sudo=True)

    _guest_id_uniq = models.Constraint(
        'unique(guest_id_type, guest_id_number)',
        'A guest with the same ID type and number already exists.')

    def _compute_guest_currency(self):
        for partner in self:
            partner.guest_currency_id = self.env.company.currency_id

    @api.depends(
        'hotel_reservation_ids.state',
        'hotel_reservation_ids.amount_total',
        'hotel_reservation_ids.checkout_date')
    def _compute_guest_stats(self):
        for partner in self:
            reservations = partner.hotel_reservation_ids
            done = reservations.filtered(lambda r: r.state == 'checked_out')
            partner.guest_reservation_count = len(reservations)
            partner.guest_stay_count = len(done)
            partner.guest_total_spent = sum(done.mapped('amount_total'))
            partner.guest_last_stay = max(done.mapped('checkout_date')) if done else False

    @api.constrains('guest_birthdate')
    def _check_guest_birthdate(self):
        today = fields.Date.context_today(self)
        for partner in self:
            if partner.guest_birthdate and partner.guest_birthdate > today:
                raise ValidationError(self.env._('Date of birth cannot be in the future.'))

    def action_view_hotel_reservations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Reservations'),
            'res_model': 'hotel.reservation',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }