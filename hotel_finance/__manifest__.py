{
    'name': 'Hotel Finance',
    'version': '19.0.1.0.0',
    'category': 'Hotel',
    'author': 'Ibrahem Issa',
    'summary': 'Taxes, deposit payments, expenses and profitability report',
    'depends': ['hotel_restaurant'],
    'data': [
        'security/hotel_finance_security.xml',
        'security/ir.model.access.csv',
        'views/hotel_hotel_views.xml',
        'views/hotel_reservation_views.xml',
        'views/hotel_expense_views.xml',
        'views/hotel_profit_report_views.xml',
        'views/hotel_finance_menus.xml',
    ],
    'license': 'LGPL-3',
}