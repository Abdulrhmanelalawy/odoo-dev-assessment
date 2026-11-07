{
    "name": "POS Salesperson on Receipt Layout",
    "summary": "Integration module: prints the line salesperson inside the receipt layout table",
    "description": """
POS Salesperson on Receipt Layout
=================================

Installed automatically when both *POS Salesperson Assignment* and *POS Receipt Layout* are
installed. The receipt layout replaces the standard order-line rendering (where the salesperson
is printed) by its own table; this module adds the salesperson to that table through the
layout's per-line extension point, so that neither module has to depend on the other.
""",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "author": "Abdelrahman Khaled",
    "website": "https://github.com/Abdulrhmanelalawy",
    "license": "LGPL-3",
    "depends": ["pos_salesperson_assignment", "pos_receipt_layout"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_salesperson_receipt_layout/static/src/**/*",
        ],
        "web.assets_tests": [
            "pos_salesperson_receipt_layout/static/tests/tours/**/*",
        ],
    },
    "auto_install": True,
    "installable": True,
}
