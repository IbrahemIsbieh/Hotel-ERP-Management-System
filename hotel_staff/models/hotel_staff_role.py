from odoo import fields, models

DEPARTMENTS = [
    ('front_desk', 'Front Desk'),
    ('housekeeping', 'Housekeeping'),
    ('restaurant', 'Restaurant & Kitchen'),
    ('maintenance', 'Maintenance'),
    ('security', 'Security'),
    ('management', 'Management'),
]


class HotelStaffRole(models.Model):
    _name = 'hotel.staff.role'
    _description = 'Hotel Staff Role'

    name = fields.Char(required=True, translate=True)
    department = fields.Selection(DEPARTMENTS, required=True)
    description = fields.Text('Responsibilities')

    _name_dept_uniq = models.Constraint(
        'unique(name, department)', 'This role already exists in the department.')