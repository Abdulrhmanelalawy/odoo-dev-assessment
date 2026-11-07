# POS Salesperson on Receipt Layout

`pos_salesperson_receipt_layout` · Odoo 19.0 · LGPL-3

Integration module between [`pos_salesperson_assignment`](../pos_salesperson_assignment/) and
[`pos_receipt_layout`](../pos_receipt_layout/). It is **installed automatically** when both are
installed and uninstalled with either of them; it needs no configuration.

## What it does

Prints the salesperson of each order line **inside the receipt layout table**, under the product
name, when both features are enabled on the point of sale.

## Why a separate module

The two POS modules are designed to be installed independently. Installed together, they meet
on the receipt, and the integration is isolated here instead of making one module depend on the
other.

| Interaction | How it is handled |
|---|---|
| **Salesperson lost on the receipt layout.** `pos_salesperson_assignment` prints the salesperson through the standard order-line component, which `pos_receipt_layout` replaces with its own table. | `pos_receipt_layout` exposes a per-line extension point (`pos_receipt_layout.ReceiptLineExtra`); this module fills it with the salesperson. |
| **Install order and optional features.** A hard dependency between the two modules would force installing a feature a customer may not want. | `depends` on both + `auto_install: True`: present only when both features are. |
| **Competing template inheritance.** Both modules extend the receipt, the point of sale form and the settings page. | Only `extension` inheritance with `attributes`, `before`, `after` or `inside` (never `replace`), each module anchored on different nodes and settings sections. |
| **Patches of the same JavaScript classes.** | Every `patch()` calls `super`, and the modules patch different methods. |
| **Field name clashes** on `pos.config` / `pos.order.line`. | Field names checked against `point_of_sale` and the Odoo 19 POS add-ons. |

## Files

```
static/src/receipt_line_salesperson.xml   extends pos_receipt_layout.ReceiptLineExtra
```

## Tests

| Test | Verifies |
|---|---|
| `test_module_is_auto_installed` | Module flagged as auto-installed |
| `test_salesperson_on_receipt_layout_tour` *(tour)* | Salesperson assigned in the POS is printed once, inside the layout table, and saved on the line |
