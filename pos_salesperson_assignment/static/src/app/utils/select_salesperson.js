// Shared salesperson picker used by the line icon and the order-level button.
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";

/**
 * Open the (reusable, core) SelectionPopup listing the salespersons loaded for this POS.
 *
 * Works offline: the list comes from the local `pos.sale.person` records.
 *
 * @param {Object} pos       pos store
 * @param {Object} dialog    dialog service
 * @param {Object} [current] salesperson currently assigned (highlighted)
 * @param {Object} [options]
 * @param {boolean} [options.allowClear] add a "No salesperson" entry (default: when `current` is set)
 * @returns {Promise<{salesperson: Object|false}|undefined>} undefined when the popup is dismissed,
 *          `{salesperson: false}` when "No salesperson" is picked.
 */
export async function selectSalesperson(pos, dialog, current = null, { allowClear = Boolean(current) } = {}) {
    const salespersons = pos.models["pos.sale.person"].getAll();
    const list = salespersons.map((person) => ({
        id: person.id,
        label: person.phone_number ? `${person.name} (${person.phone_number})` : person.name,
        isSelected: current?.id === person.id,
        item: { salesperson: person },
    }));
    if (allowClear) {
        list.push({ id: 0, label: _t("No salesperson"), isSelected: false, item: { salesperson: false } });
    }
    return makeAwaitable(dialog, SelectionPopup, {
        title: _t("Select a salesperson"),
        list,
    });
}
