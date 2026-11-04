from odoo import api, fields, models


class HotelHotel(models.Model):
    _name = 'hotel.hotel'
    _description = 'Hotel'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    star_rating = fields.Selection(
        [('1', '1 Star'), ('2', '2 Stars'), ('3', '3 Stars'),
         ('4', '4 Stars'), ('5', '5 Stars')], default='3')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    street = fields.Char()
    city = fields.Char()
    country_id = fields.Many2one('res.country')
    phone = fields.Char()
    email = fields.Char()
    check_in_time = fields.Float(default=14.0)
    check_out_time = fields.Float(default=12.0)

    building_ids = fields.One2many('hotel.building', 'hotel_id')
    room_ids = fields.One2many('hotel.room', 'hotel_id')
    building_count = fields.Integer(compute='_compute_counts')
    room_count = fields.Integer(compute='_compute_counts')
    total_capacity = fields.Integer(compute='_compute_counts')

    _code_uniq = models.Constraint(
        'unique(code, company_id)', 'Hotel code must be unique per company.')

    @api.depends('building_ids', 'room_ids', 'room_ids.max_guests')
    def _compute_counts(self):
        for hotel in self:
            hotel.building_count = len(hotel.building_ids)
            hotel.room_count = len(hotel.room_ids)
            hotel.total_capacity = sum(hotel.room_ids.mapped('max_guests'))

    def action_view_rooms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Rooms'),
            'res_model': 'hotel.room',
            'view_mode': 'list,form',
            'domain': [('hotel_id', '=', self.id)],
            'context': {'default_hotel_id': self.id},
        }