// Product screen action bar: "Salesperson" button assigning one salesperson to the whole order.
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { selectSalesperson } from "@pos_salesperson_assignment/app/utils/select_salesperson";

patch(ControlButtons.prototype, {
    /**
     * Assign one salesperson to every line currently in the order.
     * Policy: the global assignment OVERWRITES previous per-line assignments.
     */
    async clickAssignSalespersonToOrder() {
        const order = this.currentOrder;
        const lines = order?.lines || [];
        if (!lines.length) {
            this.notification.add(_t("Add a product to the order first."), { type: "warning" });
            return;
        }
        const assigned = new Set(lines.map((line) => line.salesperson_id?.id || false));
        const current = assigned.size === 1 ? lines[0].salesperson_id : null;
        const result = await selectSalesperson(this.pos, this.dialog, current, {
            allowClear: [...assigned].some(Boolean),
        });
        if (!result) {
            return;
        }
        for (const line of lines) {
            line.update({ salesperson_id: result.salesperson || false });
        }
    },
});
