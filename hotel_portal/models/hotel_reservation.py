from odoo import api, fields, models


class HotelReservation(models.Model):
    _inherit = ['hotel.reservation', 'portal.mixin']

    portal_booking = fields.Boolean('Online Booking', readonly=True, copy=False)
    service_request_ids = fields.One2many('hotel.service.request', 'reservation_id')
    service_request_count = fields.Integer(compute='_compute_service_request_count')

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/my/reservations/%s' % rec.id

    @api.depends('service_request_ids')
    def _compute_service_request_count(self):
        for rec in self:
            rec.service_request_count = len(rec.service_request_ids)

    def _portal_can_cancel(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return (self.state in ('draft', 'confirmed')
                and (self.checkin_date - today).days >= self.hotel_id.portal_cancel_days)

    def action_view_service_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Service Requests'),
            'res_model': 'hotel.service.request',
            'view_mode': 'list,form',
            'domain': [('reservation_id', '=', self.id)],
            'context': {'default_reservation_id': self.id},
        }