from odoo import api, fields, models
from odoo.exceptions import UserError


class HotelReservationCharge(models.Model):
    _name = 'hotel.reservation.charge'
    _description = 'Reservation Extra Charge'
    _order = 'date, id'

    reservation_id = fields.Many2one('hotel.reservation', required=True, ondelete='cascade')
    date = fields.Datetime(default=fields.Datetime.now, required=True)
    name = fields.Char('Description', required=True)
    product_id = fields.Many2one('product.product', domain=[('sale_ok', '=', True)])
    quantity = fields.Float(default=1.0, required=True)
    price_unit = fields.Monetary(currency_field='currency_id', required=True)
    subtotal = fields.Monetary(compute='_compute_subtotal', store=True,
                               currency_field='currency_id')
    currency_id = fields.Many2one(related='reservation_id.currency_id')

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.price_unit = self.product_id.lst_price

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            reservation = self.env['hotel.reservation'].browse(vals.get('reservation_id'))
            if reservation.state != 'checked_in':
                raise UserError(self.env._(
                    'Extra charges can only be added while the guest is checked in.'))
        return super().create(vals_list)