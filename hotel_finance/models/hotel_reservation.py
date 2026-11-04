from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class HotelReservation(models.Model):
    _inherit = 'hotel.reservation'

    deposit_journal_id = fields.Many2one(
        'account.journal', compute='_compute_deposit_journal_id',
        store=True, readonly=False,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]")
    deposit_payment_id = fields.Many2one('account.payment', readonly=True, copy=False)
    deposit_refund_payment_id = fields.Many2one('account.payment', readonly=True, copy=False)
    invoice_payment_state = fields.Char(
        'Payment Status', compute='_compute_invoice_payment_state', compute_sudo=True)

    @api.depends('hotel_id')
    def _compute_deposit_journal_id(self):
        for rec in self:
            rec.deposit_journal_id = rec.hotel_id.payment_journal_id

    @api.depends('invoice_id.payment_state')
    def _compute_invoice_payment_state(self):
        for rec in self:
            rec.invoice_payment_state = rec.invoice_id.payment_state or False

    # ---------- taxes ----------
    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        stay = self.env.ref('hotel_frontdesk.product_hotel_stay')
        for command in vals['invoice_line_ids']:
            line_vals = command[2]
            taxes = (self.hotel_id.stay_tax_ids
                     if line_vals['product_id'] == stay.id
                     else self.hotel_id.service_tax_ids)
            line_vals['tax_ids'] = [Command.set(taxes.ids)]
        return vals

    # ---------- deposit payments ----------
    def _create_deposit_payment(self, payment_type):
        self.ensure_one()
        journal = self.sudo().deposit_journal_id
        if not journal:
            raise UserError(self.env._(
                'Set a deposit journal on the reservation or on the hotel first.'))
        payment = self.env['account.payment'].sudo().with_company(self.company_id).create({
            'payment_type': payment_type,
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'amount': self.deposit_amount,
            'journal_id': journal.id,
            'memo': self.env._('Deposit %(rsv)s', rsv=self.name),
        })
        payment.action_post()
        return payment

    def action_receive_deposit(self):
        todo = self.filtered(lambda r: r.deposit_state == 'none')
        res = super(HotelReservation, todo).action_receive_deposit()
        for rec in todo:
            rec.deposit_payment_id = rec._create_deposit_payment('inbound')
        return res

    def action_refund_deposit(self):
        held = self.filtered(lambda r: r.deposit_state == 'held')
        res = super(HotelReservation, held).action_refund_deposit()
        for rec in held:
            rec.deposit_refund_payment_id = rec._create_deposit_payment('outbound')
        return res

    # ---------- check-out ----------
    def _reconcile_deposit(self, invoice):
        self.ensure_one()
        pay_lines = self.deposit_payment_id.sudo().move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
        inv_lines = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
        if pay_lines and inv_lines:
            (inv_lines + pay_lines).reconcile()

    def action_check_out(self):
        res = super().action_check_out()
        for rec in self:
            invoice = rec.invoice_id.sudo()
            deposit_applied = rec.deposit_state == 'applied' and rec.deposit_payment_id
            if invoice.state == 'draft' and (rec.hotel_id.auto_post_invoice or deposit_applied):
                invoice.action_post()
            if deposit_applied and invoice.state == 'posted':
                rec._reconcile_deposit(invoice)
        return res