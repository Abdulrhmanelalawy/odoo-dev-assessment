// Order line model: never merge a product into a line credited to another salesperson.
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    /**
     * Adding the same product again must not merge it into a line credited to another
     * salesperson (the quantity would be credited to the wrong person).
     */
    canBeMergedWith(orderline) {
        if ((this.salesperson_id?.id || false) !== (orderline.salesperson_id?.id || false)) {
            return false;
        }
        return super.canBeMergedWith(...arguments);
    },
});
