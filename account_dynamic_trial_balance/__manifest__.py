{
    "name": "Dynamic Trial Balance",
    "summary": "Configurable trial balance with account hierarchy, multi-currency breakdown "
               "and on-screen, PDF and Excel outputs",
    "description": """
Dynamic Trial Balance
=====================

A trial balance report driven by a wizard:

* Initial balance, period movement and ending balance (debit, credit, balance)
* Posted entries, optionally with draft entries (cancelled entries never included)
* Account filter by code prefixes, journal and analytic account filters
* Account-group hierarchy with subtotals, or parent groups only down to a chosen level
* Breakdown by transaction currency with the amount in currency
* Interactive on-screen preview (OWL), PDF (QWeb) and XLSX exports sharing one engine
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Abdelrahman Khaled",
    "website": "https://github.com/Abdulrhmanelalawy",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "report/trial_balance_report.xml",
        "wizard/trial_balance_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "demo": [
        "demo/trial_balance_demo_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_dynamic_trial_balance/static/src/preview/**/*",
        ],
    },
    "external_dependencies": {"python": ["xlsxwriter"]},
    "installable": True,
    "application": False,
}
