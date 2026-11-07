# Dynamic Trial Balance

`account_dynamic_trial_balance` · Odoo 19.0 · LGPL-3

A configurable trial balance for Odoo Accounting. A wizard collects the period, options and
filters; the result can be explored on screen or exported to PDF and Excel. All three outputs
are produced by the same calculation engine and therefore always show the same figures.

---

## Features

### Report columns

For every account (and every account group or total line):

| Section | Debit | Credit | Balance |
|---|---|---|---|
| **Initial Balance** — everything before the start date | net debit position | net credit position | debit − credit |
| **Movement** — journal items within the period | sum of debits | sum of credits | debit − credit |
| **End Balance** — initial + movement | net debit position | net credit position | debit − credit |

### Options and filters

| Option | Behaviour |
|---|---|
| **Period** | Start and end date. |
| **Include Unposted Entries** | Draft entries are reported together with the posted ones. Cancelled entries are never reported. |
| **Hierarchy and Subtotals** | Accounts grouped by *account group* (any depth) with a subtotal per group. |
| **Hierarchy Only Parents** + **Account Level Up To** | Group lines only, from level 1 down to the selected level (1–5). |
| **Accounts** | One or several code prefixes entered as tags (e.g. `10`, `4`, `6011`). An account is reported when its code starts with any of them. Empty: all accounts. |
| **Journals** | Restrict to the selected journals. Empty: all journals. |
| **Analytic Accounts** | Keep journal items whose analytic distribution contains one of the selected analytic accounts. Empty: no analytic filter. |
| **Skip Zero Balance** | Hide accounts having neither an initial balance nor any transaction in the period. |
| **Show Amount Currency** | One line per *account × transaction currency*, with an *Amount Currency* column showing the sum in that currency and its symbol. |

### Outputs

| Output | Description |
|---|---|
| **Preview** | Interactive report inside Odoo: change the period and the options live, search accounts by code or name (parent groups are kept), fold / unfold groups, click an account to open its journal items, export the current view to PDF or XLSX. The view survives a page reload. |
| **PDF** | A4 landscape. Title, company, period and active filters on top; column header repeated on every page; footer with company, print date and page number. |
| **XLSX** | Two-level header, number formats, bold group and total rows, Excel outline levels following the account hierarchy (collapsible), frozen header and account columns. |

### Accounting rules

- **Profit & loss accounts** (income and expense) start every fiscal year at zero: their initial
  balance only includes the current fiscal year.
- The **result of the previous fiscal years** is reported in the initial balance of the
  *Current Year Earnings* account (`equity_unaffected`), so an unfiltered report always balances.
- Initial and end Debit / Credit columns show the **net position** of the account (a debit
  balance in Debit, a credit balance in Credit); the Movement columns show **gross** debits and
  credits.
- The report covers the company selected in the company switcher.

---

## Usage

1. *Accounting → Reporting → Dynamic Trial Balance*.
2. Choose the period, the options and the filters.
3. Click **Preview**, **PDF** or **XLSX**.

Access: users of the accounting groups *Read-only*, *Basic* and *Administrator*.

---

## Technical design

```
 wizard (dynamic.trial.balance.wizard)          OWL client action (Preview)
        │  _get_report_options()                        │ orm.call
        └───────────────┬───────────────────────────────┘
                        ▼
      dynamic.trial.balance.engine.get_report_data(options)
                        │  _read_group on account.move.line (SQL GROUP BY)
                        ▼
          {header, options, lines[], total, company_currency}
             │                 │                    │
        QWeb PDF report   XLSX (xlsxwriter)   OWL table
```

| Component | File | Role |
|---|---|---|
| `dynamic.trial.balance.engine` | `models/trial_balance_engine.py` | Stateless engine: options in, report lines out. Two aggregated queries (initial and period) plus one for the previous years' result. |
| `dynamic.trial.balance.wizard` | `wizard/trial_balance_wizard.py` | Options form, Preview / PDF / XLSX actions, XLSX writer. |
| `dynamic.trial.balance.prefix` | `models/trial_balance_prefix.py` | Account-code prefixes used as tags in the wizard. |
| XLSX endpoint | `controllers/main.py` | Streams the Excel file (`/account_dynamic_trial_balance/xlsx/<id>`). |
| PDF report | `report/trial_balance_report.xml` | QWeb template and landscape paper format. |
| Preview | `static/src/preview/` | OWL client action `account_dynamic_trial_balance.preview`. |
| Demo data | `models/trial_balance_demo_data.py` | Account-group tree, analytic plan and sample entries. |

**Why a dedicated engine instead of `account_reports`?** The module only depends on `account`,
so it runs on Community and Enterprise alike, and every option (prefix list, level cut-off,
currency breakdown) is implemented in readable, unit-tested Python instead of being bent into the
generic report framework.

---

## Demo data

Installed with demo data, the module creates (idempotently):

- a four-level account-group tree (`1 → 10 → 101 → 1010`) built from the existing chart of
  accounts when the localization has no groups;
- an analytic plan *Departments* with *Sales* and *Administration*;
- eight journal entries over the last year and the current month: posted, **draft** and
  **cancelled** entries, one in a **foreign currency**, several with analytic distributions.

---

## Tests

`tests/test_trial_balance.py` builds a small, fully known dataset (dedicated account groups
`88 → 881 → 8811 / 8812` and `88 → 8888`, six entries: previous fiscal year, posted, draft,
cancelled, second journal, foreign currency, analytic) and checks the nine figures of every
account for each option.

| Test | Verifies |
|---|---|
| `test_posted_figures` | Initial / movement / end figures per account; P&L reset at fiscal year start |
| `test_full_report_balances` | Unfiltered grand total nets to zero in every section |
| `test_previous_years_result_on_unaffected_earnings` | Previous years' result on *Current Year Earnings* |
| `test_unposted_entries` | Draft entries on demand, cancelled entries never |
| `test_account_prefix_filter` | Several prefixes combined; LIKE wildcards matched literally |
| `test_journal_filter` · `test_analytic_filter` | Journal-item filters |
| `test_skip_zero_balance` | Zero accounts hidden |
| `test_hierarchy_subtotals` | Order, levels, parents and subtotals of groups |
| `test_hierarchy_only_parents` | Level cut-off, groups only |
| `test_amount_currency_breakdown` | One line per currency with the right amount in currency |
| `test_access_accounting_administrator` | Accounting administrators can run the report |
| `test_invalid_period` | Inverted period rejected |
| `test_wizard_outputs` | Preview action, PDF rendering and XLSX content |

```bash
odoo-bin -c odoo.conf -d test_db -i account_dynamic_trial_balance \
  --test-enable --test-tags /account_dynamic_trial_balance --stop-after-init
```
