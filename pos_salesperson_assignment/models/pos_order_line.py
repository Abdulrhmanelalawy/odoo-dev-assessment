"""Salesperson credited on each POS order line."""

from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    salesperson_id = fields.Many2one("pos.sale.person", string="Salesperson", index="btree_not_null")

    @api.model
    def _load_pos_data_fields(self, config):
        # Loading the field also makes the POS send it back when the order is synced.
        return [*super()._load_pos_data_fields(config), "salesperson_id"]
