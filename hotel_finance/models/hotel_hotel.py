from odoo import fields, models


class HotelHotel(models.Model):
    _inherit = 'hotel.hotel'

    stay_tax_ids = fields.Many2many(
        'account.tax', 'hotel_hotel_stay_tax_rel', 'hotel_id', 'tax_id',
        string='Stay Taxes',
        domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', company_id)]")
    service_tax_ids = fields.Many2many(
        'account.tax', 'hotel_hotel_service_tax_rel', 'hotel_id', 'tax_id',
        string='Services Taxes',
        domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', company_id)]")
    payment_journal_id = fields.Many2one(
        'account.journal', string='Deposit / Payment Journal',
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]")
    auto_post_invoice = fields.Boolean(
        'Auto-post Invoice at Check-out', default=True,
        help='If disabled, the invoice stays in draft after check-out '
             'for accounting review (unless a deposit was applied).')