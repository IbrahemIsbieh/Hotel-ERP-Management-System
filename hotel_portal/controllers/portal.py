from urllib.parse import urlencode

from odoo import Command, _, fields, http
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class HotelCustomerPortal(CustomerPortal):

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _reservation_domain(self):
        return [('partner_id', 'child_of', [request.env.user.commercial_partner_id.id])]

    def _state_labels(self):
        field = request.env['hotel.reservation']._fields['state']
        return dict(field._description_selection(request.env))

    def _flash_messages(self):
        return {
            'booked': _('Your reservation is confirmed. Thank you!'),
            'booked_pending': _('Your booking request was received. The hotel will confirm it shortly.'),
            'cancelled': _('Your reservation was cancelled.'),
            'request_sent': _('Your request was sent to the hotel.'),
        }

    def _error_messages(self):
        return {
            'invalid': _('Invalid search. Please check the form and try again.'),
            'past': _('Arrival date cannot be in the past.'),
            'dates': _('Departure must be after arrival.'),
            'too_long': _('This stay exceeds the maximum number of nights for online booking.'),
            'guests': _('At least one adult is required.'),
            'unavailable': _('Sorry, this room type is no longer available for these dates.'),
            'confirm_failed': _('We could not confirm your booking. Please contact the hotel.'),
            'cancel_not_allowed': _('This reservation can no longer be cancelled online.'),
            'cancel_failed': _('We could not cancel this reservation. Please contact the hotel.'),
            'bad_request': _('Your request could not be processed.'),
        }

    def _get_reservation(self, reservation_id, access_token=None):
        try:
            return self._document_check_access(
                'hotel.reservation', reservation_id, access_token=access_token)
        except (AccessError, MissingError):
            return None

    def _parse_search(self, hotel_id, checkin, checkout, adults, children):
        Hotel = request.env['hotel.hotel'].sudo()
        today = fields.Date.context_today(request.env.user)
        res = {'hotel': Hotel, 'checkin': False, 'checkout': False,
               'adults': 1, 'children': 0, 'error': False, 'searched': False}
        try:
            res['hotel'] = Hotel.browse(int(hotel_id)).exists() if hotel_id else Hotel
            res['adults'] = int(adults or 1)
            res['children'] = int(children or 0)
            res['checkin'] = fields.Date.to_date(checkin) if checkin else False
            res['checkout'] = fields.Date.to_date(checkout) if checkout else False
        except (ValueError, TypeError):
            res['error'] = 'invalid'
            return res
        hotel, cin, cout = res['hotel'], res['checkin'], res['checkout']
        if not (hotel and cin and cout):
            return res
        res['searched'] = True
        if not hotel.portal_bookable:
            res['error'] = 'invalid'
        elif cin < today:
            res['error'] = 'past'
        elif cout <= cin:
            res['error'] = 'dates'
        elif (cout - cin).days > hotel.portal_max_nights:
            res['error'] = 'too_long'
        elif res['adults'] < 1 or res['children'] < 0:
            res['error'] = 'guests'
        return res

    def _redirect_new(self, params, error):
        query = {
            'hotel_id': params['hotel'].id or '',
            'checkin': params['checkin'] or '',
            'checkout': params['checkout'] or '',
            'adults': params['adults'],
            'children': params['children'],
            'error': error,
        }
        return request.redirect('/my/reservations/new?%s' % urlencode(query))

    # ------------------------------------------------------------------
    # /my home counter
    # ------------------------------------------------------------------
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'reservation_count' in counters:
            Reservation = request.env['hotel.reservation']
            values['reservation_count'] = (
                Reservation.search_count(self._reservation_domain())
                if Reservation.has_access('read') else 0)
        return values

    # ------------------------------------------------------------------
    # list
    # ------------------------------------------------------------------
    @http.route(['/my/reservations', '/my/reservations/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_reservations(self, page=1, sortby=None, **kw):
        Reservation = request.env['hotel.reservation']
        domain = self._reservation_domain()
        searchbar_sortings = {
            'date': {'label': _('Arrival (latest first)'), 'order': 'checkin_date desc, id desc'},
            'date_asc': {'label': _('Arrival (earliest first)'), 'order': 'checkin_date asc, id asc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state, checkin_date desc'},
        }
        sortby = sortby if sortby in searchbar_sortings else 'date'
        total = Reservation.search_count(domain)
        pager = portal_pager(
            url='/my/reservations', url_args={'sortby': sortby},
            total=total, page=page, step=self._items_per_page)
        reservations = Reservation.search(
            domain, order=searchbar_sortings[sortby]['order'],
            limit=self._items_per_page, offset=pager['offset'])
        values = self._prepare_portal_layout_values()
        values.update({
            'reservations': reservations,
            'page_name': 'reservation',
            'pager': pager,
            'default_url': '/my/reservations',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'state_labels': self._state_labels(),
        })
        return request.render('hotel_portal.portal_my_reservations', values)

    # ------------------------------------------------------------------
    # booking (must come before the <int:id> route to avoid clashes)
    # ------------------------------------------------------------------
    @http.route('/my/reservations/new', type='http', auth='user', website=True)
    def portal_reservation_new(self, hotel_id=None, checkin=None, checkout=None,
                               adults=None, children=None, error=None, **kw):
        hotels = request.env['hotel.hotel'].sudo().search([('portal_bookable', '=', True)])
        params = self._parse_search(hotel_id, checkin, checkout, adults, children)
        error = error or params['error']
        results = []
        if params['searched'] and not params['error']:
            hotel, cin, cout = params['hotel'], params['checkin'], params['checkout']
            nights = (cout - cin).days
            rooms = hotel._portal_get_available_rooms(cin, cout).filtered(
                lambda r: r.room_type_id.portal_visible)
            for rtype in rooms.room_type_id:
                if params['adults'] > rtype.max_adults or \
                        params['adults'] + params['children'] > rtype.max_guests:
                    continue
                room = hotel._portal_pick_room(rtype, cin, cout)
                if not room:
                    continue
                total = room._get_stay_price(cin, cout)
                results.append({
                    'room_type': rtype,
                    'available': len(rooms.filtered(lambda r: r.room_type_id == rtype)),
                    'total': total,
                    'per_night': total / nights if nights else total,
                    'nights': nights,
                })
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'reservation',
            'hotels': hotels,
            'params': params,
            'results': results,
            'today': fields.Date.context_today(request.env.user),
            'error_message': self._error_messages().get(error),
        })
        return request.render('hotel_portal.portal_reservation_new', values)

    @http.route('/my/reservations/book', type='http', auth='user',
                methods=['POST'], website=True)
    def portal_reservation_book(self, hotel_id=None, room_type_id=None, checkin=None,
                                checkout=None, adults=None, children=None, notes=None, **kw):
        params = self._parse_search(hotel_id, checkin, checkout, adults, children)
        if not params['searched'] or params['error']:
            return self._redirect_new(params, params['error'] or 'invalid')
        hotel = params['hotel']
        try:
            room_type = request.env['hotel.room.type'].sudo().browse(int(room_type_id)).exists()
        except (ValueError, TypeError):
            room_type = False
        if not room_type or not room_type.portal_visible or \
                params['adults'] > room_type.max_adults or \
                params['adults'] + params['children'] > room_type.max_guests:
            return self._redirect_new(params, 'invalid')

        room = hotel._portal_pick_room(room_type, params['checkin'], params['checkout'])
        if not room:
            return self._redirect_new(params, 'unavailable')

        partner = request.env.user.partner_id
        reservation = request.env['hotel.reservation'].sudo().create({
            'hotel_id': hotel.id,
            'partner_id': partner.id,
            'checkin_date': params['checkin'],
            'checkout_date': params['checkout'],
            'adults': params['adults'],
            'children': params['children'],
            'notes': (notes or '').strip()[:1000],
            'portal_booking': True,
            'line_ids': [Command.create({'room_id': room.id})],
        })

        message = 'booked_pending'
        if hotel.portal_auto_confirm:
            try:
                with request.env.cr.savepoint():
                    reservation.action_confirm()
                message = 'booked'
            except (UserError, ValidationError):
                # Generic message on purpose: never expose internal reasons
                # (e.g. blacklist details) to the portal user.
                reservation.invalidate_recordset()
                reservation.unlink()
                return self._redirect_new(params, 'confirm_failed')

        reservation.message_post(
            body=_('Online booking received from the customer portal.'),
            message_type='comment', subtype_xmlid='mail.mt_comment',
            partner_ids=partner.ids)
        return request.redirect(reservation.get_portal_url(query_string='&message=%s' % message))

    # ------------------------------------------------------------------
    # detail
    # ------------------------------------------------------------------
    @http.route('/my/reservations/<int:reservation_id>', type='http', auth='public', website=True)
    def portal_reservation_page(self, reservation_id, access_token=None,
                                message=None, error=None, **kw):
        reservation = self._get_reservation(reservation_id, access_token)
        if not reservation:
            return request.redirect('/my')
        invoice = reservation.invoice_id
        invoice_url = invoice.get_portal_url() if invoice and invoice.state == 'posted' else False
        request_types = dict(
            request.env['hotel.service.request']._fields['request_type']
            ._description_selection(request.env))
        values = {
            'reservation': reservation,
            'page_name': 'reservation',
            'token': access_token,
            'state_labels': self._state_labels(),
            'can_cancel': reservation._portal_can_cancel(),
            'can_request': reservation.state in ('confirmed', 'checked_in'),
            'request_types': request_types,
            'invoice_url': invoice_url,
            'flash': self._flash_messages().get(message),
            'error_message': self._error_messages().get(error),
        }
        return request.render('hotel_portal.portal_reservation_page', values)

    @http.route('/my/reservations/<int:reservation_id>/cancel', type='http',
                auth='public', methods=['POST'], website=True)
    def portal_reservation_cancel(self, reservation_id, access_token=None, **kw):
        reservation = self._get_reservation(reservation_id, access_token)
        if not reservation:
            return request.redirect('/my')
        if not reservation._portal_can_cancel():
            return request.redirect(reservation.get_portal_url(query_string='&error=cancel_not_allowed'))
        try:
            reservation.action_cancel()
        except UserError:
            return request.redirect(reservation.get_portal_url(query_string='&error=cancel_failed'))
        reservation.message_post(
            body=_('Reservation cancelled by the customer from the portal.'))
        return request.redirect(reservation.get_portal_url(query_string='&message=cancelled'))

    @http.route('/my/reservations/<int:reservation_id>/request', type='http',
                auth='public', methods=['POST'], website=True)
    def portal_reservation_request(self, reservation_id, access_token=None,
                                   request_type=None, description=None, **kw):
        reservation = self._get_reservation(reservation_id, access_token)
        if not reservation:
            return request.redirect('/my')
        valid_types = dict(
            request.env['hotel.service.request']._fields['request_type']
            ._description_selection(request.env))
        description = (description or '').strip()[:2000]
        if reservation.state not in ('confirmed', 'checked_in') \
                or request_type not in valid_types or not description:
            return request.redirect(reservation.get_portal_url(query_string='&error=bad_request'))
        request.env['hotel.service.request'].sudo().create({
            'reservation_id': reservation.id,
            'request_type': request_type,
            'description': description,
        })
        return request.redirect(reservation.get_portal_url(query_string='&message=request_sent'))