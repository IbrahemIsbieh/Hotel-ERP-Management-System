from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HotelSeason(models.Model):
    _name = 'hotel.season'
    _description = 'Pricing Season'
    _order = 'date_from'

    name = fields.Char(required=True)
    hotel_id = fields.Many2one('hotel.hotel', required=True, ondelete='cascade')
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    price_ids = fields.One2many('hotel.season.price', 'season_id')

    @api.constrains('date_from', 'date_to', 'hotel_id')
    def _check_dates(self):
        for rec in self:
            if rec.date_to < rec.date_from:
                raise ValidationError(self.env._('Season end date must be after its start date.'))
            overlap = self.search([
                ('id', '!=', rec.id),
                ('hotel_id', '=', rec.hotel_id.id),
                ('date_from', '<=', rec.date_to),
                ('date_to', '>=', rec.date_from),
            ], limit=1)
            if overlap:
                raise ValidationError(self.env._(
                    'Season "%(a)s" overlaps with "%(b)s".',
                    a=rec.name, b=overlap.name))


class HotelSeasonPrice(models.Model):
    _name = 'hotel.season.price'
    _description = 'Seasonal Room Type Price'

    season_id = fields.Many2one('hotel.season', required=True, ondelete='cascade')
    room_type_id = fields.Many2one('hotel.room.type', required=True)
    price = fields.Monetary(currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    _season_type_uniq = models.Constraint(
        'unique(season_id, room_type_id)',
        'Only one price per room type in each season.')