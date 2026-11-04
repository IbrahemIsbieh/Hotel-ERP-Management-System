from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class HotelDashboard(models.AbstractModel):
    _name = 'hotel.dashboard'
    _description = 'Hotel BI Dashboard'

    def _selection_labels(self, model, field):
        return dict(self.env[model]._fields[field]._description_selection(self.env))

    @api.model
    def get_data(self, hotel_id=False, date_from=False, date_to=False):
        if not self.env.user.has_group('hotel_finance.group_hotel_accountant'):
            raise AccessError(self.env._('You are not allowed to view the hotel dashboard.'))

        today = fields.Date.context_today(self)
        date_from = fields.Date.to_date(date_from) or today.replace(day=1)
        date_to = fields.Date.to_date(date_to) or (date_from + relativedelta(months=1, days=-1))
        if date_to < date_from:
            raise UserError(self.env._('The end date must be after the start date.'))
        if (date_to - date_from).days > 366:
            raise UserError(self.env._('The period cannot exceed one year.'))

        Hotel = self.env['hotel.hotel']
        hotel = Hotel.browse(hotel_id).exists() if hotel_id else Hotel
        hdom = [('hotel_id', '=', hotel.id)] if hotel else []
        currency = hotel.currency_id or self.env.company.currency_id

        # ---------------- capacity ----------------
        Room = self.env['hotel.room']
        rooms = Room.search_count(hdom + [('state', '!=', 'out_of_service')])
        days = (date_to - date_from).days + 1
        available_nights = rooms * days

        # ---------------- occupancy (SQL view) ----------------
        Occ = self.env['hotel.occupancy.report']
        occ_domain = hdom + [('date', '>=', date_from), ('date', '<=', date_to)]
        by_day = {
            day: (count, revenue)
            for day, count, revenue in Occ._read_group(
                occ_domain, ['date:day'], ['__count', 'night_rate:sum'])
        }
        series = []
        sold = 0
        room_revenue = 0.0
        day = date_from
        while day <= date_to:
            count, revenue = by_day.get(day, (0, 0.0))
            sold += count
            room_revenue += revenue
            series.append({
                'date': fields.Date.to_string(day),
                'sold': count,
                'revenue': round(revenue, 2),
                'occupancy': round(count / rooms * 100, 1) if rooms else 0.0,
            })
            day += timedelta(days=1)

        occupancy = round(sold / available_nights * 100, 1) if available_nights else 0.0
        adr = round(room_revenue / sold, 2) if sold else 0.0
        revpar = round(room_revenue / available_nights, 2) if available_nights else 0.0

        types = Occ._read_group(
            occ_domain, ['room_type_id'], ['__count', 'night_rate:sum'])
        room_types = sorted(
            ({'name': rtype.display_name, 'nights': count, 'revenue': round(revenue, 2)}
             for rtype, count, revenue in types),
            key=lambda x: -x['revenue'])[:6]

        # ---------------- financials (SQL view from hotel_finance) ----------------
        Profit = self.env['hotel.profit.report']
        pdom = hdom + [('date', '>=', date_from), ('date', '<=', date_to)]
        by_type = {t: a for t, a in Profit._read_group(pdom, ['line_type'], ['amount:sum'])}
        type_labels = self._selection_labels('hotel.profit.report', 'line_type')
        sources = [
            {'key': key, 'label': type_labels[key], 'amount': round(by_type.get(key, 0.0), 2)}
            for key in ('room', 'services', 'restaurant')
        ]
        revenue = sum(s['amount'] for s in sources)
        expenses = round(by_type.get('expense', 0.0), 2)
        profit = round(revenue - expenses, 2)
        expense_categories = sorted(
            ({'label': (cat or 'other').title(), 'amount': round(amount, 2)}
             for cat, amount in Profit._read_group(
                 pdom + [('line_type', '=', 'expense')], ['category'], ['amount:sum'])),
            key=lambda x: -x['amount'])

        # ---------------- reservations in the period ----------------
        Reservation = self.env['hotel.reservation']
        rdom = hdom + [('checkin_date', '>=', date_from), ('checkin_date', '<=', date_to)]
        state_labels = self._selection_labels('hotel.reservation', 'state')
        reservations_by_state = [
            {'state': state, 'label': state_labels.get(state, state), 'count': count}
            for state, count in Reservation._read_group(rdom, ['state'], ['__count'])
        ]
        channels = {'online': 0, 'staff': 0}
        for online, count in Reservation._read_group(
                rdom + [('state', '!=', 'cancelled')], ['portal_booking'], ['__count']):
            channels['online' if online else 'staff'] += count

        # ---------------- today ----------------
        room_state_labels = self._selection_labels('hotel.room', 'state')
        room_status = [
            {'state': state, 'label': room_state_labels.get(state, state), 'count': count}
            for state, count in Room._read_group(hdom, ['state'], ['__count'])
        ]
        today_stats = {
            'date': fields.Date.to_string(today),
            'arrivals': Reservation.search_count(
                hdom + [('state', '=', 'confirmed'), ('checkin_date', '=', today)]),
            'departures': Reservation.search_count(
                hdom + [('state', '=', 'checked_in'), ('checkout_date', '=', today)]),
            'in_house': Reservation.search_count(hdom + [('state', '=', 'checked_in')]),
            'requests': self.env['hotel.service.request'].search_count(
                hdom + [('state', 'in', ('new', 'in_progress'))]),
            'cleaning': self.env['hotel.housekeeping.task'].search_count(
                hdom + [('state', 'in', ('pending', 'in_progress', 'done'))]),
            'staff_on_duty': self.env['hotel.shift.assignment'].search_count(
                hdom + [('date', '=', today), ('state', 'in', ('planned', 'confirmed'))]),
        }

        return {
            'currency': {'symbol': currency.symbol, 'position': currency.position},
            'period': {
                'from': fields.Date.to_string(date_from),
                'to': fields.Date.to_string(date_to),
                'days': days,
            },
            'rooms': rooms,
            'kpis': {
                'occupancy': occupancy,
                'adr': adr,
                'revpar': revpar,
                'room_nights_sold': sold,
                'available_nights': available_nights,
                'room_revenue': round(room_revenue, 2),
                'revenue': round(revenue, 2),
                'expenses': expenses,
                'profit': profit,
                'margin': round(profit / revenue * 100, 1) if revenue else 0.0,
            },
            'series': series,
            'sources': sources,
            'expense_categories': expense_categories,
            'room_types': room_types,
            'reservations_by_state': reservations_by_state,
            'channels': channels,
            'room_status': room_status,
            'today': today_stats,
        }