"""Salesperson master data, available in the POS (including offline)."""

from odoo import api, fields, models


class PosSalePerson(models.Model):
    """Salesperson credited for POS order lines.

    Inherits ``pos.load.mixin`` so the records are shipped to the POS with the session data and
    stay available offline (the POS keeps its data in IndexedDB).
    """

    _name = "pos.sale.person"
    _description = "POS Salesperson"
    _inherit = ["pos.load.mixin"]
    _order = "name, id"

    name = fields.Char(required=True)
    phone_number = fields.Char(string="Phone Number")
    employee_id = fields.Many2one(
        "hr.employee",
        string="Related Employee",
        help="Optional link to an employee, e.g. to compute commissions in payroll.",
    )
    active = fields.Boolean(default=True)

    @api.model
    def _load_pos_data_domain(self, data, config):
        if not config.active_salesperson_feature:
            return False  # feature disabled: nothing is loaded
        if config.allowed_sale_person_ids:
            return [("id", "in", config.allowed_sale_person_ids.ids)]
        return []  # no restriction configured: every active salesperson

    @api.model
    def _load_pos_data_fields(self, config):
        # employee_id is backend-only: hr.employee is not loaded in the POS without pos_hr.
        return ["id", "name", "phone_number"]
