{
    'name': 'Hotel Guest',
    'version': '19.0.1.0.0',
    'category': 'Hotel',
    'author': 'Ibrahem Issa',
    'summary': 'Guest profiles, history, VIP levels and blacklist',
    'depends': ['hotel_reservation'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/hotel_reservation_views.xml',
        'views/hotel_guest_menus.xml',
    ],
    'license': 'LGPL-3',
}