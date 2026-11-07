"""Ships the salespersons to the POS with the session data."""

from odoo import api, models


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_data_models(self, config):
        # Always declared so the order-line relation resolves; the domain loads no record
        # when the feature is disabled on the config.
        return [*super()._load_pos_data_models(config), "pos.sale.person"]
