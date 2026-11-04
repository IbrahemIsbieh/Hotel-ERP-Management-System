{
    'name': 'Hotel Core',
    'version': '19.0.1.0.0',
    'category': 'Hotel',
    'summary': 'Hotels, buildings, floors, room types and rooms',
    'author': 'Ibrahem Issa',
    'depends': ['base','mail'],
    'data': [
        'security/hotel_security.xml',
        'security/ir.model.access.csv',
        'views/hotel_views.xml',
        'views/hotel_room_views.xml',
        'views/hotel_menus.xml',
    ],

    'application': True,
    'license': 'LGPL-3',
}