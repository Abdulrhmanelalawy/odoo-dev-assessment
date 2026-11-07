{
    "name": "POS Receipt Layout",
    "summary": "Per point of sale receipt layout: logo, company header, customer details and a table of order lines",
    "description": """
POS Receipt Layout
==================

Optional, per point of sale receipt layout:

* Dedicated receipt logo (cached for offline printing)
* Company name and details as rich text, above the standard receipt details
* Customer name and address on demand
* Order lines in a Product / Qty / Price / Total table
* Standard Odoo receipt kept untouched when the layout is disabled
""",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "author": "Abdelrahman Khaled",
    "website": "https://github.com/Abdulrhmanelalawy",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/pos_config_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_receipt_layout/static/src/**/*",
        ],
        "web.assets_tests": [
            "pos_receipt_layout/static/tests/tours/**/*",
        ],
    },
    "installable": True,
}
