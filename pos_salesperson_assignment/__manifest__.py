{
    "name": "POS Salesperson Assignment",
    "summary": "Credit a salesperson on each Point of Sale order line, per line or for the whole order",
    "description": """
POS Salesperson Assignment
==========================

* Salesperson master data (name, phone, optional employee) available offline in the POS
* Per point of sale activation and list of allowed salespersons
* Assignment per order line (icon on the line) or for the whole order (action button)
* Salesperson printed under the product name on the receipt
* Salesperson stored on the order line and visible in the backend (filter / group by)
""",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "author": "Abdelrahman Khaled",
    "website": "https://github.com/Abdulrhmanelalawy",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_sale_person_views.xml",
        "views/pos_config_views.xml",
        "views/res_config_settings_views.xml",
        "views/pos_order_line_views.xml",
    ],
    "demo": [
        "demo/pos_sale_person_demo.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_salesperson_assignment/static/src/**/*",
        ],
        "web.assets_tests": [
            "pos_salesperson_assignment/static/tests/tours/**/*",
        ],
    },
    "installable": True,
}
