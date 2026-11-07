# POS Receipt Layout

`pos_receipt_layout` · Odoo 19.0 · LGPL-3

An optional receipt layout, configured **per point of sale**: dedicated logo, company header,
customer details and order lines printed in a clear table. Points of sale that do not enable it
keep the standard Odoo receipt, untouched.

---

## Features

When **Receipt Layout** is enabled on a point of sale:

| Setting | On the receipt |
|---|---|
| **Receipt Logo** | Printed at the top. Falls back to the company logo when empty. |
| **Company Name** (rich text) | Under the logo, before the standard receipt details. |
| **Company Details** (rich text) | Under the company name: address, phone, tax id... |
| **Show Customer Details** | Customer name and address printed, or hidden. |
| — | Order lines in a **Product / Qty / Price / Total** table, with discounts, line notes and combo items. |

When the layout is disabled, all these settings are ignored and the standard receipt is printed.

---

## Configuration

*Point of Sale → Configuration → Settings*, select the point of sale, section *Bills & Receipts*
→ **Receipt Layout** (the same settings are available in the point of sale form). Reload the POS
to apply the changes.

---

## Technical design

| Concern | Implementation |
|---|---|
| No core override | `point_of_sale.OrderReceipt` and `point_of_sale.ReceiptHeader` are extended with `t-inherit-mode="extension"` + `xpath`; every change is conditional on `use_customized_receipt`. |
| Logo, including offline | The POS already caches the receipt logo as a data URL when it starts (`PosConfig.cacheReceiptLogo`). The module only overrides `receiptCompanyLogoUrl`, so the layout logo benefits from the same cache. The image is not sent in the session payload: `_load_pos_data_read` replaces it with a `_has_receipt_logo` flag. |
| Rich text safety | *Company Name* and *Company Details* are `fields.Html(sanitize=True)`; they are rendered with OWL `markup()` only after server-side sanitization, so a configuration editor cannot inject scripts into the POS. |
| Order lines table | Same line ordering as the standard receipt (combo parents followed by their items) and the standard line price helpers, so totals and rounding are identical. |
| Extension point | Each table row calls the empty template `pos_receipt_layout.ReceiptLineExtra` with `line` in scope: other modules can add per-line information without overriding the table (used by `pos_salesperson_receipt_layout`). |
| Styling | `static/src/scss/receipt_layout.scss` (logo, typography, table borders and spacing). |

```
models/pos_config.py              settings + session payload
models/res_config_settings.py     settings page fields
static/src/app/receipt/
  pos_config.js                   receipt logo source
  receipt_header.js / .xml        company block, customer details switch
  order_receipt.js / .xml         lines table + extension point
static/src/scss/receipt_layout.scss
```

---

## Tests

`tests/test_receipt_layout.py`, browser tours in `static/tests/tours/`.

| Test | Verifies |
|---|---|
| `test_html_fields_are_sanitized` | Scripts removed, formatting kept |
| `test_logo_not_shipped_in_session_payload` | Flag instead of the image in the POS data |
| `test_receipt_layout_tour` *(tour)* | Logo, rich-text company name and details, customer details, lines table, standard list replaced |
| `test_receipt_layout_without_customer_tour` *(tour)* | Customer details hidden when disabled |
| `test_default_receipt_tour` *(tour)* | Layout disabled: standard receipt even with every setting filled |

```bash
odoo-bin -c odoo.conf -d test_db -i pos_receipt_layout \
  --test-enable --test-tags /pos_receipt_layout --stop-after-init
```
