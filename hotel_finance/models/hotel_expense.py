from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HotelExpense(models.Model):
    _name = 'hotel.expense'
    _description = 'Hotel Operating Expense'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char('Description', required=True)
    hotel_id = fields.Many2one('hotel.hotel', required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    category = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('utilities', 'Utilities'),
        ('supplies', 'Supplies'),
        ('salaries', 'Salaries'),
        ('marketing', 'Marketing'),
        ('food', 'Food & Beverage Cost'),
        ('other', 'Other'),
    ], default='other', required=True)
    partner_id = fields.Many2one('res.partner', string='Vendor')
    amount = fields.Monetary(currency_field='currency_id', required=True, tracking=True)
    currency_id = fields.Many2one(related='hotel_id.currency_id')
    company_id = fields.Many2one(related='hotel_id.company_id', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True, copy=False)
    notes = fields.Text()

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(self.env._('The amount must be greater than zero.'))

    def action_approve(self):
        self.filtered(lambda r: r.state == 'draft').write({'state': 'approved'})

    def action_pay(self):
        self.filtered(lambda r: r.state == 'approved').write({'state': 'paid'})

    def action_cancel(self):
        self.filtered(lambda r: r.state in ('draft', 'approved')).write({'state': 'cancelled'})

    def action_draft(self):
        self.filtered(lambda r: r.state == 'cancelled').write({'state': 'draft'})