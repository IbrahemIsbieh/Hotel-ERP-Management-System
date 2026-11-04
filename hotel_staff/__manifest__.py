{
    'name': 'Hotel Staff',
    'version': '19.0.1.0.0',
    'category': 'Hotel',
    'author': 'Ibrahem Issa',
    'summary': 'Staff roles, shifts, schedules and housekeeping assignment',
    'depends': ['hr', 'hotel_housekeeping'],
    'data': [
        'security/ir.model.access.csv',
        'views/hotel_staff_views.xml',
        'views/hotel_shift_assignment_views.xml',
        'views/hr_employee_views.xml',
        'views/hotel_housekeeping_views.xml',
        'views/hotel_staff_menus.xml',
    ],
    'license': 'LGPL-3',
}