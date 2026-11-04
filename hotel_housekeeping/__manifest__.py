{
    'name': 'Hotel Housekeeping',
    'version': '19.0.1.0.0',
    'category': 'Hotel',
    'author': 'Ibrahem Issa',
    'summary': 'Cleaning tasks, checklists, inspection and room release',
    'depends': ['hotel_frontdesk'],
    'data': [
        'security/hotel_housekeeping_security.xml',
        'security/ir.model.access.csv',
        'data/hotel_housekeeping_data.xml',
        'views/hotel_housekeeping_views.xml',
        'views/hotel_room_views.xml',
        'views/hotel_housekeeping_menus.xml',
    ],
    'license': 'LGPL-3',
}