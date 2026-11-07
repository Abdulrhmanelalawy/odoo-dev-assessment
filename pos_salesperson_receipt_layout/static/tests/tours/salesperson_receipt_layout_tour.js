// Browser tour: salesperson printed inside the receipt layout table (run by tests/test_salesperson_receipt_layout.py).

import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosSalespersonOnReceiptLayoutTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            {
                content: "assign a salesperson to the line",
                trigger: `.product-screen .orderline:has(.product-name:contains("Desk Organizer")) .o_pos_assign_salesperson`,
                run: "click",
            },
            SelectionPopup.has("Salesperson A", { run: "click" }),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            {
                content: "receipt layout table shows the salesperson under the product",
                trigger: ".pos-receipt table.o_pos_receipt_layout_lines tr:contains('Desk Organizer') .o_pos_salesperson_name:contains('Salesperson A')",
            },
            {
                content: "salesperson printed once (no duplicate from the core line rendering)",
                trigger: ".pos-receipt:not(:has(.order-container))",
            },
        ].flat(),
});
