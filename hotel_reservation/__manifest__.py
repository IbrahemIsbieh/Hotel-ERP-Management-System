{
    'name': 'Hotel Reservation',
    'version': '19.0.1.0.0',
    'category': 'Hotel Reservation',
    'summary': 'Reservations, availability, seasonal prices',
    'author': 'Ibrahem Issa',
    'depends': ['hotel_core','mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/hotel_reservation_data.xml',
        'views/hotel_season_views.xml',
        'views/hotel_reservation_views.xml',
        'views/hotel_reservation_menus.xml',

    ],
    'license': 'LGPL-3',
}