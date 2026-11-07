"""Per-POS receipt layout options."""

from odoo import fields, models


class PosConfig(models.Model):
    """Receipt layout settings, independent for each point of sale.

    When ``use_customized_receipt`` is off, none of the other fields has any effect and the
    standard Odoo receipt is printed.
    """

    _inherit = "pos.config"

    use_customized_receipt = fields.Boolean(
        string="Receipt Layout",
        help="Print the receipts of this point of sale with the receipt layout (logo, company "
             "name and details, customer details, order lines in a table). When disabled, the "
             "standard Odoo receipt is printed.",
    )
    receipt_logo = fields.Image(
        string="Receipt Logo",
        max_width=512, max_height=512,
        help="Printed at the top of the receipt. Falls back to the company logo when empty.",
    )
    # Rich text (formatting allowed) sanitized server side: the POS renders it as markup, so
    # a configuration editor must not be able to inject scripts into every cashier's POS.
    company_name = fields.Html(string="Receipt Company Name", sanitize=True, sanitize_style=True)
    company_details = fields.Html(string="Receipt Company Details", sanitize=True, sanitize_style=True)
    show_customer_details = fields.Boolean(
        string="Show Customer Details",
        help="Print the customer's name and address on the receipt.",
    )

    def _load_pos_data_read(self, records, config):
        """Replace the logo by a ``_has_receipt_logo`` flag in the POS session payload."""
        read_records = super()._load_pos_data_read(records, config)
        for record in read_records:
            # Do not ship the image itself in the session payload: the POS fetches it once
            # through /web/image and caches it as a data URL (see PosConfig.cacheReceiptLogo),
            # which keeps it available offline.
            record["_has_receipt_logo"] = bool(record.pop("receipt_logo", False))
        return read_records
