# Odoo 19 Business Add-ons

A set of Odoo 19 modules for **accounting reporting** and **Point of Sale**, built with the
standard Odoo framework (ORM, QWeb, OWL), fully tested, with no change to Odoo's core code.

| Module | Area | What it does |
|---|---|---|
| [`account_dynamic_trial_balance`](account_dynamic_trial_balance/) | Accounting | Configurable trial balance: initial / movement / ending balances, account hierarchy, multi-currency, on-screen preview, PDF and Excel |
| [`pos_salesperson_assignment`](pos_salesperson_assignment/) | Point of Sale | Credit a salesperson on each order line or on the whole order, offline-ready, printed on the receipt |
| [`pos_receipt_layout`](pos_receipt_layout/) | Point of Sale | Per point of sale receipt layout: logo, company header, customer details, table of order lines |
| [`pos_salesperson_receipt_layout`](pos_salesperson_receipt_layout/) | Point of Sale | Integration module (auto-installed) printing the salesperson inside the receipt layout |

---

## Highlights

**Dynamic Trial Balance**
- One calculation engine shared by the on-screen report, the PDF and the XLSX export: the three
  outputs can never disagree.
- Aggregation done in SQL through the ORM (`_read_group`), so record rules and multi-company
  security apply and performance does not depend on the number of journal items.
- Odoo accounting rules respected: cancelled entries excluded, P&L accounts reset at the start
  of the fiscal year, previous years' result carried on *Current Year Earnings*.
- Interactive OWL preview: live options, search, foldable account groups, drill-down to journal
  items, export of exactly what is on screen.

**Point of Sale**
- Salespersons are part of the POS data: assignment keeps working **offline** and is synced
  with the order.
- Everything is optional **per point of sale**; when a feature is off, the standard POS and
  receipt are untouched.
- The two POS features are independent modules; a small auto-installed module makes them work
  together (see [design notes](pos_salesperson_receipt_layout/README.md)).

---

## Compatibility

| | |
|---|---|
| Odoo | 19.0 (Community or Enterprise) |
| Dependencies | `account` · `point_of_sale` · `hr` |
| Python | `xlsxwriter` (shipped with Odoo) |
| License | [LGPL-3](LICENSE) |

## Installation

1. Clone the repository next to your other add-ons:
   ```bash
   git clone https://github.com/Abdulrhmanelalawy/odoo-dev-assessment.git
   ```
2. Add the cloned folder to the `addons_path` of your Odoo configuration file, then restart Odoo.
3. In Odoo, enable the developer mode, open *Apps → Update Apps List* and install the modules you
   need. Installing both POS modules installs the integration module automatically.

## Configuration at a glance

| Module | Where |
|---|---|
| Dynamic Trial Balance | *Accounting → Reporting → Dynamic Trial Balance* |
| Salesperson Assignment | *Point of Sale → Configuration → Settings → PoS Interface → Salesperson Assignment*, salespersons in *Configuration → Salespersons* |
| Receipt Layout | *Point of Sale → Configuration → Settings → Bills & Receipts → Receipt Layout* |

Each module README describes its features, configuration, technical design and tests.

## Tests

The repository ships **27 automated tests**: Python unit tests for the business logic and
browser tours driving the real POS interface (including an order validated while offline).

```bash
odoo-bin -c odoo.conf -d test_db --stop-after-init --test-enable \
  -i account_dynamic_trial_balance,pos_salesperson_assignment,pos_receipt_layout \
  --test-tags /account_dynamic_trial_balance,/pos_salesperson_assignment,/pos_receipt_layout,/pos_salesperson_receipt_layout
```

| Module | Tests |
|---|---|
| `account_dynamic_trial_balance` | 14 |
| `pos_salesperson_assignment` | 6 (2 browser tours) |
| `pos_receipt_layout` | 5 (3 browser tours) |
| `pos_salesperson_receipt_layout` | 2 (1 browser tour) |

Browser tours require Google Chrome and the `websocket-client` Python package on the Odoo server.

## Repository layout

```
account_dynamic_trial_balance/     Accounting report (engine, wizard, PDF, XLSX, OWL preview)
pos_salesperson_assignment/        Salesperson model, POS UI, receipt, backend views
pos_receipt_layout/                POS receipt layout (header, customer, lines table)
pos_salesperson_receipt_layout/    Integration of the two POS modules
```

## Author

**Abdelrahman Khaled** — [github.com/Abdulrhmanelalawy](https://github.com/Abdulrhmanelalawy)
