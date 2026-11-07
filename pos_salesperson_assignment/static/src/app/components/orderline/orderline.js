// Order line: per-line salesperson button (product screen) and salesperson name (screen + receipt).
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { patch } from "@web/core/utils/patch";
import { selectSalesperson } from "@pos_salesperson_assignment/app/utils/select_salesperson";

patch(Orderline.prototype, {
    get showSalespersonButton() {
        return this.props.mode === "display" && Boolean(this.line.config?.active_salesperson_feature);
    },

    get showSalespersonName() {
        return Boolean(this.line.config?.active_salesperson_feature && this.line.salesperson_id);
    },

    /** Assign a salesperson to this line only. */
    async onClickAssignSalesperson() {
        // Services are read lazily: Orderline is also rendered by the receipt printer.
        const { pos, dialog } = this.env.services;
        const result = await selectSalesperson(pos, dialog, this.line.salesperson_id);
        if (result) {
            this.line.update({ salesperson_id: result.salesperson || false });
        }
    },
});
