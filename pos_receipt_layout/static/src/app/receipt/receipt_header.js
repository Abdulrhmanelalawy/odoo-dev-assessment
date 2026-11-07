// Receipt header: company name / details block and the customer details switch.
import { markup } from "@odoo/owl";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { patch } from "@web/core/utils/patch";

/** Html field values are sanitized server side (fields.Html(sanitize=True)). */
function htmlOrFalse(value) {
    const text = (value || "").replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ").trim();
    return text ? markup(value) : false;
}

patch(ReceiptHeader.prototype, {
    get isCustomizedReceipt() {
        return Boolean(this.order.config.use_customized_receipt);
    },

    get customCompanyName() {
        return this.isCustomizedReceipt && htmlOrFalse(this.order.config.company_name);
    },

    get customCompanyDetails() {
        return this.isCustomizedReceipt && htmlOrFalse(this.order.config.company_details);
    },

    get showCustomerDetails() {
        if (!this.order.partner_id) {
            return false;
        }
        return !this.isCustomizedReceipt || Boolean(this.order.config.show_customer_details);
    },
});
