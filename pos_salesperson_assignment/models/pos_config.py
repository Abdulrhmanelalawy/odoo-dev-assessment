"""Point of Sale configuration: per-POS activation and allowed salespersons."""

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    active_salesperson_feature = fields.Boolean(
        string="Salesperson Assignment",
        help="Allow cashiers to assign a salesperson to each order line or to the whole order.",
    )
    allowed_sale_person_ids = fields.Many2many(
        "pos.sale.person",
        string="Allowed Salespersons",
        help="Salespersons available in this point of sale. Leave empty to allow all of them.",
    )
