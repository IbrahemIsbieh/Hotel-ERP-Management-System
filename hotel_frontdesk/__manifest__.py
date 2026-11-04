{
    'name': 'Hotel Front Desk',
    'version': '19.0.1.0.0',
    'category': 'Hotel',
    'author': 'Ibrahem Issa',
    'summary': 'Check-in, check-out, deposits, extra charges and invoicing',
    'depends': ['hotel_guest', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/hotel_frontdesk_data.xml',
        'views/hotel_reservation_views.xml',
        'views/hotel_frontdesk_menus.xml',
    ],
    'license': 'LGPL-3',
}