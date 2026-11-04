/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const pad = (n) => String(n).padStart(2, "0");
const fmtDate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

export class HotelDashboard extends Component {
    static template = "hotel_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const now = new Date();
        this.state = useState({
            loading: true,
            error: false,
            hotels: [],
            hotelId: false,
            dateFrom: fmtDate(new Date(now.getFullYear(), now.getMonth(), 1)),
            dateTo: fmtDate(new Date(now.getFullYear(), now.getMonth() + 1, 0)),
            data: null,
        });

        onWillStart(async () => {
            this.state.hotels = await this.orm.searchRead("hotel.hotel", [], ["name"]);
            await this.load();
        });
    }

    async load() {
        this.state.loading = true;
        this.state.error = false;
        try {
            this.state.data = await this.orm.call("hotel.dashboard", "get_data", [], {
                hotel_id: this.state.hotelId || false,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
            });
        } catch (error) {
            this.state.error = true;
            throw error;
        } finally {
            this.state.loading = false;
        }
    }

    // ---------- filters ----------
    onHotelChange(ev) {
        const value = ev.target.value;
        this.state.hotelId = value ? parseInt(value, 10) : false;
        this.load();
    }

    onDateFromChange(ev) {
        if (ev.target.value) {
            this.state.dateFrom = ev.target.value;
            this.load();
        }
    }

    onDateToChange(ev) {
        if (ev.target.value) {
            this.state.dateTo = ev.target.value;
            this.load();
        }
    }

    setPreset(preset) {
        const now = new Date();
        let from;
        let to;
        if (preset === "month") {
            from = new Date(now.getFullYear(), now.getMonth(), 1);
            to = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        } else if (preset === "30d") {
            to = now;
            from = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 29);
        } else {
            from = new Date(now.getFullYear(), 0, 1);
            to = new Date(now.getFullYear(), 11, 31);
        }
        this.state.dateFrom = fmtDate(from);
        this.state.dateTo = fmtDate(to);
        this.load();
    }

    // ---------- formatting ----------
    num(value, digits = 0) {
        return new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(
            value || 0
        );
    }

    money(value) {
        const { symbol, position } = this.state.data.currency;
        const formatted = this.num(value);
        return position === "before" ? `${symbol}${formatted}` : `${formatted} ${symbol}`;
    }

    // ---------- view models ----------
    get kpis() {
        const k = this.state.data.kpis;
        return [
            { key: "occ", label: "Occupancy", value: `${this.num(k.occupancy, 1)}%`,
              sub: `${this.num(k.room_nights_sold)} / ${this.num(k.available_nights)} room nights`,
              icon: "fa-bed", cls: "text-primary" },
            { key: "adr", label: "ADR", value: this.money(k.adr),
              sub: "Average daily rate", icon: "fa-tag", cls: "text-info" },
            { key: "revpar", label: "RevPAR", value: this.money(k.revpar),
              sub: "Revenue per available room", icon: "fa-line-chart", cls: "text-info" },
            { key: "rev", label: "Revenue", value: this.money(k.revenue),
              sub: "Rooms + services + restaurant", icon: "fa-money", cls: "text-success" },
            { key: "exp", label: "Expenses", value: this.money(k.expenses),
              sub: "Approved / paid", icon: "fa-credit-card", cls: "text-danger" },
            { key: "profit", label: "Net Profit", value: this.money(k.profit),
              sub: `Margin ${this.num(k.margin, 1)}%`, icon: "fa-balance-scale",
              cls: k.profit >= 0 ? "text-success" : "text-danger" },
        ];
    }

    get dailyBars() {
        return this.state.data.series.map((s) => ({
            date: s.date,
            height: Math.max(s.occupancy, 0.5),
            title: `${s.date}: ${s.occupancy}% occupancy, ${s.sold} room nights, ${this.money(s.revenue)}`,
        }));
    }

    _hbars(items, labelKey, valueKey) {
        const max = Math.max(...items.map((i) => Math.abs(i[valueKey])), 1);
        return items.map((i) => ({
            label: i[labelKey],
            value: i[valueKey],
            width: Math.round((Math.abs(i[valueKey]) / max) * 100),
            extra: i.nights !== undefined ? `${i.nights} nights` : "",
        }));
    }

    get sourceBars() {
        return this._hbars(this.state.data.sources, "label", "amount");
    }

    get roomTypeBars() {
        return this._hbars(this.state.data.room_types, "name", "revenue");
    }

    get expenseBars() {
        return this._hbars(this.state.data.expense_categories, "label", "amount");
    }

    get todayItems() {
        const t = this.state.data.today;
        return [
            { key: "arrivals", label: "Arrivals", value: t.arrivals, icon: "fa-sign-in" },
            { key: "departures", label: "Departures", value: t.departures, icon: "fa-sign-out" },
            { key: "in_house", label: "In-house guests", value: t.in_house, icon: "fa-users" },
            { key: "requests", label: "Open requests", value: t.requests, icon: "fa-bell-o" },
            { key: "cleaning", label: "Cleaning tasks", value: t.cleaning, icon: "fa-eraser" },
            { key: "staff", label: "Staff on duty", value: t.staff_on_duty, icon: "fa-id-badge" },
        ];
    }

    // ---------- drill-down ----------
    openToday(key) {
        const hotel = this.state.hotelId ? [["hotel_id", "=", this.state.hotelId]] : [];
        const today = this.state.data.today.date;
        const defs = {
            arrivals: ["hotel.reservation", "Arrivals Today",
                [["state", "=", "confirmed"], ["checkin_date", "=", today]]],
            departures: ["hotel.reservation", "Departures Today",
                [["state", "=", "checked_in"], ["checkout_date", "=", today]]],
            in_house: ["hotel.reservation", "In-House Guests", [["state", "=", "checked_in"]]],
            requests: ["hotel.service.request", "Open Requests",
                [["state", "in", ["new", "in_progress"]]]],
            cleaning: ["hotel.housekeeping.task", "Cleaning Tasks",
                [["state", "in", ["pending", "in_progress", "done"]]]],
            staff: ["hotel.shift.assignment", "Staff on Duty",
                [["date", "=", today], ["state", "in", ["planned", "confirmed"]]]],
        };
        const [model, name, domain] = defs[key];
        this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            domain: [...hotel, ...domain],
        });
    }

    openOccupancyAnalysis() {
        this.action.doAction("hotel_dashboard.action_hotel_occupancy_report");
    }
}

registry.category("actions").add("hotel_dashboard", HotelDashboard);