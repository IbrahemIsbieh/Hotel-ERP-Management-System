from odoo import api, fields, models


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'
    _inherit = ['mail.thread']
    _order = 'hotel_id, floor_id, name'

    name = fields.Char('Room Number', required=True, tracking=True)
    hotel_id = fields.Many2one('hotel.hotel', required=True, tracking=True)
    building_id = fields.Many2one(
        'hotel.building', domain="[('hotel_id', '=', hotel_id)]")
    floor_id = fields.Many2one(
        'hotel.floor', required=True,
        domain="[('hotel_id', '=', hotel_id)]")
    room_type_id = fields.Many2one('hotel.room.type', required=True, tracking=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Maintenance'),
        ('out_of_service', 'Out of Service'),
    ], default='available', required=True, tracking=True)
    active = fields.Boolean(default=True)

    max_guests = fields.Integer(related='room_type_id.max_guests', store=True)
    amenity_ids = fields.Many2many(related='room_type_id.amenity_ids')
    price_override = fields.Monetary(currency_field='currency_id',
                                     help='Leave empty to use the room type price.')
    price = fields.Monetary(compute='_compute_price', currency_field='currency_id')
    currency_id = fields.Many2one(related='hotel_id.currency_id')
    notes = fields.Text()

    _name_uniq = models.Constraint(
        'unique(hotel_id, name)', 'Room number must be unique per hotel.')

    @api.depends('price_override', 'room_type_id.base_price')
    def _compute_price(self):
        for room in self:
            room.price = room.price_override or room.room_type_id.base_price

    @api.onchange('floor_id')
    def _onchange_floor_id(self):
        if self.floor_id:
            self.building_id = self.floor_id.building_id

    def action_set_available(self):
        self.write({'state': 'available'})

    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_set_out_of_service(self):
        self.write({'state': 'out_of_service'})