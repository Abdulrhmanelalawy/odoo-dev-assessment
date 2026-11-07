// Browser tours of the receipt layout (run by tests/test_receipt_layout.py).

import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import { registry } from "@web/core/registry";

function saleWithCustomer() {
    return [
        Chrome.startPoS(),
        Dialog.confirm("Open Register"),
        ProductScreen.clickDisplayedProduct("Desk Organizer"),
        ProductScreen.clickDisplayedProduct("Letter Tray"),
        ProductScreen.clickPartnerButton(),
        ProductScreen.clickCustomer("Partner Full"),
        ProductScreen.clickPayButton(),
        PaymentScreen.clickPaymentMethod("Bank"),
        PaymentScreen.clickValidate(),
        ReceiptScreen.receiptIsThere(),
    ].flat();
}

const check = (content, trigger) => ({ content, trigger });

registry.category("web_tour.tours").add("PosReceiptLayoutTour", {
    steps: () => [
        ...saleWithCustomer(),
        check("custom logo is printed", ".pos-receipt img.pos-receipt-logo"),
        check("company name (HTML) is rendered", ".pos-receipt .o_pos_receipt_layout_company_name b:contains('My Custom Shop')"),
        check("company details are rendered", ".pos-receipt .o_pos_receipt_layout_company_details:contains('Street 1, Cairo')"),
        check("customer details are printed", ".pos-receipt .pos-receipt-customer:contains('Partner Full')"),
        check("order lines are a table", ".pos-receipt table.o_pos_receipt_layout_lines tbody tr:contains('Desk Organizer')"),
        check("both lines are in the table", ".pos-receipt table.o_pos_receipt_layout_lines tbody tr:contains('Letter Tray')"),
        check("default list rendering is replaced", ".pos-receipt:not(:has(.order-container))"),
        check("no script survived the HTML sanitizer", ".pos-receipt:not(:has(script))"),
    ],
});

registry.category("web_tour.tours").add("PosReceiptLayoutNoCustomerTour", {
    steps: () => [
        ...saleWithCustomer(),
        check("order lines are a table", ".pos-receipt table.o_pos_receipt_layout_lines"),
        check("customer details are hidden", ".pos-receipt:not(:has(.pos-receipt-customer))"),
    ],
});

registry.category("web_tour.tours").add("PosDefaultReceiptTour", {
    steps: () => [
        ...saleWithCustomer(),
        check("standard list rendering", ".pos-receipt .order-container .orderline:contains('Desk Organizer')"),
        check("no table", ".pos-receipt:not(:has(table.o_pos_receipt_layout_lines))"),
        check("no layout company block", ".pos-receipt:not(:has(.o_pos_receipt_layout_company))"),
        check("standard customer block kept", ".pos-receipt .pos-receipt-customer:contains('Partner Full')"),
    ],
});
