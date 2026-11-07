// Order receipt: order lines rendered as a table when the receipt layout is enabled.
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    get isCustomizedReceipt() {
        return Boolean(this.order.config.use_customized_receipt);
    },

    /** Same ordering as the core OrderDisplay: combo parents followed by their children. */
    get customReceiptLines() {
        return this.order.lines.reduce((lines, line) => {
            if (line.combo_line_ids?.length) {
                lines.push(line, ...line.combo_line_ids);
            } else if (!line.combo_parent_id) {
                lines.push(line);
            }
            return lines;
        }, []);
    },

    customReceiptQty(line) {
        const { unitPart, decimalPart, decimalPoint } = line.getQuantityStr();
        return decimalPart ? `${unitPart}${decimalPoint}${decimalPart}` : unitPart;
    },

    customReceiptDiscount(line) {
        const discount = line.getDiscountStr();
        return discount && discount !== "0" && !line.combo_parent_id ? discount : false;
    },
});
