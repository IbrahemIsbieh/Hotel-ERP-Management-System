{
    'name': 'Hotel Dashboard (BI)',
    'version': '19.0.1.0.0',
    'category': 'Hotel',
    'author': 'Ibrahem Issa',
    'summary': 'Occupancy, ADR, RevPAR, revenue and profitability dashboard',
    'depends': ['hotel_portal', 'hotel_staff'],
    'data': [
        'security/ir.model.access.csv',
        'views/hotel_dashboard_views.xml',
        'views/hotel_dashboard_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hotel_dashboard/static/src/css/dashboard.css',
            'hotel_dashboard/static/src/js/dashboard.js',
            'hotel_dashboard/static/src/xml/dashboard.xml',
        ],
    },
    'license': 'LGPL-3',
}