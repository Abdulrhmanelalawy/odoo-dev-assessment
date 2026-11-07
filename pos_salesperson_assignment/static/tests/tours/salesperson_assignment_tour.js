// Browser tours of the salesperson assignment (run by tests/test_salesperson_assignment.py).

import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import { registry } from "@web/core/registry";

const line = (product) => `.product-screen .orderline:has(.product-name:contains("${product}"))`;

function assignToLine(product, salesperson) {
    return [
        {
            content: `open the salesperson popup of the '${product}' line`,
            trigger: `${line(product)} .o_pos_assign_salesperson`,
            run: "click",
        },
        ...SelectionPopup.has(salesperson, { run: "click" }),
        lineHasSalesperson(product, salesperson),
    ];
}

function lineHasSalesperson(product, salesperson) {
    return {
        content: `'${product}' line is credited to ${salesperson}`,
        trigger: `${line(product)} .o_pos_salesperson_name:contains("${salesperson}")`,
    };
}

function assignToOrder(salesperson) {
    return [
        {
            content: "open the global salesperson popup",
            trigger: ".product-screen button.o_pos_assign_salesperson_order",
            run: "click",
        },
        ...SelectionPopup.has(salesperson, { run: "click" }),
    ];
}

function payAndCheckReceipt(receiptChecks = []) {
    return [
        ProductScreen.clickPayButton(),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.clickValidate(),
        ReceiptScreen.receiptIsThere(),
        ...receiptChecks,
    ];
}

function receiptHasSalesperson(product, salesperson) {
    return {
        content: `receipt shows ${salesperson} under '${product}'`,
        trigger: `.pos-receipt .orderline:has(.product-name:contains("${product}")) .o_pos_salesperson_name:contains("${salesperson}")`,
    };
}

registry.category("web_tour.tours").add("PosSalespersonAssignmentTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Per-line assignment, done OFFLINE (salespersons are part of the local POS data)
            OfflineUtil.setOfflineMode(),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            assignToLine("Desk Organizer", "Salesperson A"),
            ProductScreen.clickDisplayedProduct("Letter Tray"),
            assignToLine("Letter Tray", "Salesperson B"),
            // Adding the same product again must NOT merge into the line credited to A
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            {
                content: "a new, unassigned Desk Organizer line was created",
                trigger: `${line("Desk Organizer")}:not(:has(.o_pos_salesperson_name))`,
            },
            payAndCheckReceipt([
                receiptHasSalesperson("Desk Organizer", "Salesperson A"),
                receiptHasSalesperson("Letter Tray", "Salesperson B"),
            ]),
            Dialog.confirm("Continue with limited functionality"),
            OfflineUtil.setOnlineMode(),
            ReceiptScreen.clickNextOrder(),

            // Order-level assignment overwrites the per-line assignments
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            assignToLine("Desk Organizer", "Salesperson A"),
            ProductScreen.clickDisplayedProduct("Letter Tray"),
            assignToLine("Letter Tray", "Salesperson B"),
            assignToOrder("Salesperson C"),
            lineHasSalesperson("Desk Organizer", "Salesperson C"),
            lineHasSalesperson("Letter Tray", "Salesperson C"),
            payAndCheckReceipt([
                receiptHasSalesperson("Desk Organizer", "Salesperson C"),
                receiptHasSalesperson("Letter Tray", "Salesperson C"),
            ]),
            ReceiptScreen.clickNextOrder(),

            // Nothing assigned: no salesperson on screen, receipt or database
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            {
                content: "no salesperson on the product screen",
                trigger: `.product-screen:not(:has(.o_pos_salesperson_name))`,
            },
            payAndCheckReceipt([
                {
                    content: "no salesperson on the receipt",
                    trigger: ".pos-receipt:not(:has(.o_pos_salesperson_name))",
                },
            ]),
            ReceiptScreen.clickNextOrder(),
        ].flat(Infinity),
});

registry.category("web_tour.tours").add("PosSalespersonDisabledTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            {
                content: "no per-line salesperson icon and no global button when the feature is off",
                trigger: ".product-screen:has(.orderline):not(:has(.o_pos_assign_salesperson, .o_pos_assign_salesperson_order))",
            },
        ].flat(Infinity),
});
