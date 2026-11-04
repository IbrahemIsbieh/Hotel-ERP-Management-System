from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class HotelRestaurantOrder(models.Model):
    _name = 'hotel.restaurant.order'
    _description = 'Restaurant / Room Service Order'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(default='New', readonly=True, copy=False)
    date = fields.Datetime(default=fields.Datetime.now, required=True)
    restaurant_id = fields.Many2one('hotel.restaurant', required=True, tracking=True)
    hotel_id = fields.Many2one(related='restaurant_id.hotel_id', store=True)
    order_type = fields.Selection([
        ('dine_in', 'Dine-in'),
        ('room_service', 'Room Service'),
        ('takeaway', 'Takeaway'),
    ], default='dine_in', required=True)
    table_number = fields.Char()

    reservation_id = fields.Many2one(
        'hotel.reservation', string='Reservation', copy=False, tracking=True,
        domain="[('state', '=', 'checked_in'), ('hotel_id', '=', hotel_id)]")
    reservation_room_ids = fields.Many2many(
        'hotel.room', compute='_compute_reservation_room_ids')
    room_id = fields.Many2one('hotel.room', domain="[('id', 'in', reservation_room_ids)]")
    partner_id = fields.Many2one(
        'res.partner', string='Guest / Customer',
        compute='_compute_partner_id', store=True, readonly=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Sent to Kitchen'),
        ('preparing', 'Preparing'),
        ('served', 'Served'),
        ('billed', 'Billed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True, copy=False)

    line_ids = fields.One2many('hotel.restaurant.order.line', 'order_id', copy=True)
    currency_id = fields.Many2one(related='hotel_id.currency_id')
    amount_subtotal = fields.Monetary(compute='_compute_amounts', store=True)
    amount_service = fields.Monetary(compute='_compute_amounts', store=True)
    amount_total = fields.Monetary(compute='_compute_amounts', store=True)

    payment_method = fields.Selection(
        [('cash', 'Cash'), ('card', 'Card'), ('room', 'Charged to Room')],
        copy=False, tracking=True)
    charge_id = fields.Many2one('hotel.reservation.charge', readonly=True, copy=False)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hotel.restaurant.order') or 'New'
        return super().create(vals_list)

    # ---------- computes ----------
    @api.depends('reservation_id.line_ids.room_id')
    def _compute_reservation_room_ids(self):
        for rec in self:
            rec.reservation_room_ids = rec.reservation_id.line_ids.room_id

    @api.depends('reservation_id')
    def _compute_partner_id(self):
        for rec in self:
            if rec.reservation_id:
                rec.partner_id = rec.reservation_id.partner_id

    @api.depends('line_ids.subtotal', 'restaurant_id.service_charge_pct')
    def _compute_amounts(self):
        for rec in self:
            subtotal = sum(rec.line_ids.mapped('subtotal'))
            service = subtotal * rec.restaurant_id.service_charge_pct / 100.0
            rec.amount_subtotal = subtotal
            rec.amount_service = service
            rec.amount_total = subtotal + service

    @api.onchange('reservation_id')
    def _onchange_reservation_id(self):
        rooms = self.reservation_id.line_ids.room_id
        self.room_id = rooms if len(rooms) == 1 else False

    @api.onchange('restaurant_id')
    def _onchange_restaurant_id(self):
        if self.restaurant_id.restaurant_type == 'room_service':
            self.order_type = 'room_service'

    # ---------- constraints ----------
    @api.constrains('order_type', 'reservation_id', 'room_id')
    def _check_room_service(self):
        for rec in self:
            if rec.order_type == 'room_service' and not (rec.reservation_id and rec.room_id):
                raise ValidationError(self.env._(
                    'Room service orders require a checked-in reservation and a room.'))
            if rec.room_id and rec.room_id not in rec.reservation_id.line_ids.room_id:
                raise ValidationError(self.env._(
                    'Room %(r)s does not belong to the selected reservation.',
                    r=rec.room_id.name))

    # ---------- workflow ----------
    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(self.env._('Add at least one item to the order.'))
        self.write({'state': 'confirmed'})

    def action_prepare(self):
        self.filtered(lambda r: r.state == 'confirmed').write({'state': 'preparing'})

    def action_serve(self):
        self.filtered(lambda r: r.state == 'preparing').write({'state': 'served'})

    def action_charge_to_room(self):
        Charge = self.env['hotel.reservation.charge']
        for rec in self:
            if rec.state != 'served':
                raise UserError(self.env._('Only served orders can be billed.'))
            if not rec.reservation_id or rec.reservation_id.state != 'checked_in':
                raise UserError(self.env._('The guest must be checked in to charge a room.'))
            if rec.charge_id:
                raise UserError(self.env._('This order was already charged to a room.'))
            charge = Charge.create({
                'reservation_id': rec.reservation_id.id,
                'name': self.env._(
                    '%(outlet)s - %(order)s', outlet=rec.restaurant_id.name, order=rec.name),
                'quantity': 1,
                'price_unit': rec.amount_total,
            })
            rec.write({'charge_id': charge.id, 'payment_method': 'room', 'state': 'billed'})

    def action_register_payment(self):
        for rec in self:
            if rec.state != 'served':
                raise UserError(self.env._('Only served orders can be paid.'))
            if rec.payment_method not in ('cash', 'card'):
                raise UserError(self.env._('Choose Cash or Card as the payment method first.'))
        self.write({'state': 'billed'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'billed':
                raise UserError(self.env._('A billed order cannot be cancelled.'))
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.filtered(lambda r: r.state == 'cancelled').write({'state': 'draft'})


class HotelRestaurantOrderLine(models.Model):
    _name = 'hotel.restaurant.order.line'
    _description = 'Restaurant Order Line'

    order_id = fields.Many2one('hotel.restaurant.order', required=True, ondelete='cascade')
    item_id = fields.Many2one('hotel.menu.item', required=True)
    name = fields.Char('Description')
    quantity = fields.Float(default=1.0, required=True)
    price_unit = fields.Monetary(currency_field='currency_id', required=True)
    subtotal = fields.Monetary(compute='_compute_subtotal', store=True,
                               currency_field='currency_id')
    currency_id = fields.Many2one(related='order_id.currency_id')
    notes = fields.Char()

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('item_id')
    def _onchange_item_id(self):
        if self.item_id:
            self.name = self.item_id.name
            self.price_unit = self.item_id.price

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(self.env._('Quantity must be greater than zero.'))