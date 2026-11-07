# POS Salesperson Assignment

`pos_salesperson_assignment` · Odoo 19.0 · LGPL-3

Credit a **salesperson** on each Point of Sale order line, either line by line or for the whole
order in one click. Built for sales-performance tracking and commissions; works **offline**.

---

## Features

- **Salespersons** (*Point of Sale → Configuration → Salespersons*): name, phone number and an
  optional link to an employee (useful for HR / payroll and commission computation).
- **Per point of sale configuration**
  - *Salesperson Assignment* toggle: when off, every related UI element is hidden and no
    salesperson is loaded in that POS.
  - *Allowed Salespersons*: salespersons offered in that POS (empty: all active salespersons).
- **In the POS**
  - A person icon on every order line opens the salesperson list and assigns **that line only**.
  - A **Salesperson** button in the product-screen action bar assigns **every line of the
    order** (it also appears in the *more actions* dialog on small screens).
  - The list offers *No salesperson* to clear an assignment.
  - The salesperson is displayed **under the product name** on the order and on the receipt.
- **Backend**
  - *Point of Sale → Orders → Order Lines*: salesperson column, filters *With / Without
    Salesperson*, grouping by salesperson.
  - Salesperson column in the *Products* tab of the order form.

### Business rules

| Rule | Behaviour |
|---|---|
| Order-level assignment | Overwrites the salesperson of every existing line. Lines added afterwards start without salesperson. |
| Adding a product already in the order | Increases the existing line **only if it has the same salesperson**; otherwise a new line is created, so a quantity is never credited to the wrong person. |
| Offline | Salespersons are part of the POS data stored in the browser; assignments made offline are saved when the order is synced. |
| Configuration changes | Like every POS setting, they apply when the POS is (re)loaded. |

---

## Configuration

1. *Point of Sale → Configuration → Salespersons*: create the salespersons.
2. *Point of Sale → Configuration → Settings*, select the point of sale, section *PoS Interface*:
   enable **Salesperson Assignment** and optionally pick the **Allowed Salespersons**
   (also available in the point of sale form).
3. Open or reload the POS.

---

## Technical design

| Concern | Implementation |
|---|---|
| Model | `pos.sale.person` (`name`, `phone_number`, `employee_id`, `active`) |
| Offline availability | `pos.sale.person` inherits `pos.load.mixin` and is declared in `pos.session._load_pos_data_models`: records are shipped with the session data and kept in the POS local database. |
| Allowed salespersons | `_load_pos_data_domain` returns `False` when the feature is off (nothing loaded) and the allowed ids otherwise. Only `id`, `name` and `phone_number` are sent to the POS. |
| Persistence | `salesperson_id` is added to `pos.order.line._load_pos_data_fields`; the standard POS synchronization sends it with the order. No custom RPC. |
| Shared picker | `static/src/app/utils/select_salesperson.js` wraps the core `SelectionPopup`, used by both entry points. |
| UI extensions | `patch()` of the OWL `Orderline` component, `ControlButtons` and the `PosOrderline` model; template inheritance with `t-inherit-mode="extension"` + `xpath`. No core file or template is replaced. |

```
models/
  pos_sale_person.py        salesperson model + POS loading
  pos_config.py             toggle + allowed salespersons
  pos_order_line.py         salesperson_id + POS field loading
  pos_session.py            declares pos.sale.person to the POS
  res_config_settings.py    settings page fields
static/src/app/
  components/orderline/     line icon + salesperson name (screen and receipt)
  screens/control_buttons/  order-level "Salesperson" button
  models/pos_order_line.js  merge rule
  utils/select_salesperson.js
```

---

## Tests

`tests/test_salesperson_assignment.py`, browser tours in `static/tests/tours/`.

| Test | Verifies |
|---|---|
| `test_nothing_loaded_when_feature_disabled` | No salesperson shipped to a POS where the feature is off |
| `test_only_allowed_salespersons_loaded` | Only allowed salespersons and only the fields the POS needs |
| `test_all_active_salespersons_when_no_restriction` | Empty allow-list loads every active salesperson |
| `test_order_line_field_is_synced` | Field and model declared to the POS |
| `test_salesperson_tour` *(tour)* | Per-line assignment **made offline** and synced afterwards, no-merge rule, order-level overwrite, order without salesperson, receipt content and database values |
| `test_salesperson_ui_hidden_when_disabled` *(tour)* | No icon and no button when the feature is off |

```bash
odoo-bin -c odoo.conf -d test_db -i pos_salesperson_assignment \
  --test-enable --test-tags /pos_salesperson_assignment --stop-after-init
```
