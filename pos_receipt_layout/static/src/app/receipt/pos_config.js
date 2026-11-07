// POS configuration model: print the receipt layout logo instead of the company logo.
import { PosConfig } from "@point_of_sale/app/models/pos_config";
import { imageUrl } from "@web/core/utils/urls";
import { patch } from "@web/core/utils/patch";

patch(PosConfig.prototype, {
    /**
     * The core caches this URL as a data URL when the POS starts (`cacheReceiptLogo`), so the
     * custom logo keeps printing offline exactly like the company logo does.
     */
    get receiptCompanyLogoUrl() {
        if (this.use_customized_receipt && this._has_receipt_logo) {
            return imageUrl("pos.config", this.id, "receipt_logo", {
                unique: this.write_date,
                width: 256,
                height: 256,
            });
        }
        return super.receiptCompanyLogoUrl;
    },
});
