{
    'name': 'Hotel Restaurant & Services',
    'version': '19.0.1.0.0',
    'category': 'Hotel',
    'author': 'Ibrahem Issa',
    'summary': 'Restaurants, menus, room service and charge-to-room orders',
    'depends': ['hotel_frontdesk'],
    'data': [
        'security/hotel_restaurant_security.xml',
        'security/ir.model.access.csv',
        'data/hotel_restaurant_data.xml',
        'views/hotel_restaurant_views.xml',
        'views/hotel_restaurant_order_views.xml',
        'views/hotel_reservation_views.xml',
        'views/hotel_restaurant_menus.xml',
    ],
    'license': 'LGPL-3',
}