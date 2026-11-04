from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HotelReservation(models.Model):
    _inherit = 'hotel.reservation'

    actual_checkin = fields.Datetime(readonly=True, copy=False)
    actual_checkout = fields.Datetime(readonly=True, copy=False)

    deposit_amount = fields.Monetary(tracking=True, copy=False)
    deposit_state = fields.Selection([
        ('none', 'No Deposit'),
        ('held', 'Held'),
        ('refunded', 'Refunded'),
        ('applied', 'Applied to Bill'),
    ], default='none', required=True, copy=False, tracking=True)

    charge_ids = fields.One2many('hotel.reservation.charge', 'reservation_id')
    charges_total = fields.Monetary(compute='_compute_totals', store=True)
    grand_total = fields.Monetary(compute='_compute_totals', store=True)
    balance_due = fields.Monetary(compute='_compute_totals', store=True)

    invoice_id = fields.Many2one('account.move', readonly=True, copy=False)

    @api.depends('amount_total', 'charge_ids.subtotal', 'deposit_amount', 'deposit_state')
    def _compute_totals(self):
        for rec in self:
            rec.charges_total = sum(rec.charge_ids.mapped('subtotal'))
            rec.grand_total = rec.amount_total + rec.charges_total
            deposit = rec.deposit_amount if rec.deposit_state == 'applied' else 0.0
            rec.balance_due = rec.grand_total - deposit

    @api.constrains('deposit_amount')
    def _check_deposit(self):
        for rec in self:
            if rec.deposit_amount < 0:
                raise ValidationError(self.env._('Deposit cannot be negative.'))

    # ---------- check-in ----------
    def action_check_in(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(self.env._('Only confirmed reservations can be checked in.'))
            if rec.checkin_date > today:
                raise UserError(self.env._(
                    'Arrival date is %(d)s; check-in is not allowed before it.',
                    d=rec.checkin_date))
            if not rec.partner_id.guest_id_number:
                raise UserError(self.env._(
                    'Register the ID type and number of %(g)s before check-in.',
                    g=rec.partner_id.name))
            not_ready = rec.line_ids.room_id.filtered(lambda r: r.state != 'available')
            if not_ready:
                raise UserError(self.env._(
                    'These rooms are not ready: %(rooms)s',
                    rooms=', '.join(not_ready.mapped('name'))))
            rec.line_ids.room_id.write({'state': 'occupied'})
            rec.write({'state': 'checked_in', 'actual_checkin': fields.Datetime.now()})

    # ---------- deposit ----------
    def action_receive_deposit(self):
        for rec in self:
            if rec.deposit_amount <= 0:
                raise UserError(self.env._('Enter a deposit amount first.'))
            rec.deposit_state = 'held'

    def action_refund_deposit(self):
        self.filtered(lambda r: r.deposit_state == 'held').deposit_state = 'refunded'

    def action_apply_deposit(self):
        self.filtered(lambda r: r.deposit_state == 'held').deposit_state = 'applied'

    # ---------- check-out ----------
    def _prepare_invoice_vals(self):
        self.ensure_one()
        stay = self.env.ref('hotel_frontdesk.product_hotel_stay')
        extra = self.env.ref('hotel_frontdesk.product_hotel_charge')
        lines = []
        for line in self.line_ids:
            lines.append(Command.create({
                'product_id': stay.id,
                'name': self.env._(
                    'Room %(room)s (%(type)s) - %(rsv)s, %(frm)s to %(to)s, %(n)s night(s)',
                    room=line.room_id.name, type=line.room_type_id.name,
                    rsv=self.name, frm=self.checkin_date, to=self.checkout_date,
                    n=self.nights),
                'quantity': 1,
                'price_unit': line.price_total,
            }))
        for charge in self.charge_ids:
            lines.append(Command.create({
                'product_id': (charge.product_id or extra).id,
                'name': charge.name,
                'quantity': charge.quantity,
                'price_unit': charge.price_unit,
            }))
        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_date': fields.Date.context_today(self),
            'invoice_line_ids': lines,
        }

    def action_check_out(self):
        for rec in self:
            if rec.state != 'checked_in':
                raise UserError(self.env._('Only checked-in reservations can be checked out.'))
            if rec.deposit_state == 'held':
                raise UserError(self.env._('Refund or apply the deposit before check-out.'))
            # Front-desk staff don't need accounting rights to generate the draft invoice.
            invoice = self.env['account.move'].sudo().with_company(rec.company_id).create(
                rec._prepare_invoice_vals())
            rec.line_ids.room_id.write({'state': 'cleaning'})
            rec.write({
                'state': 'checked_out',
                'actual_checkout': fields.Datetime.now(),
                'invoice_id': invoice.id,
            })

    def action_cancel(self):
        if self.filtered(lambda r: r.deposit_state == 'held'):
            raise UserError(self.env._('Refund the deposit before cancelling.'))
        return super().action_cancel()

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }