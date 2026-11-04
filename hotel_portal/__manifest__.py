{
    'name': 'Hotel Customer Portal',
    'version': '19.0.1.0.0',
    'category': 'Hotel',
    'author': 'Ibrahem Issa',
    'summary': 'Online booking, reservation follow-up and service requests',
    'depends': ['portal', 'hotel_finance'],
    'data': [
        'security/hotel_portal_security.xml',
        'security/ir.model.access.csv',
        'data/hotel_portal_data.xml',
        'views/hotel_portal_backend_views.xml',
        'views/portal_templates.xml',
    ],
    'license': 'LGPL-3',
}