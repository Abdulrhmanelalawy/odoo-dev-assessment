"""Account-code prefixes used as search tags in the Dynamic Trial Balance wizard."""

from odoo import api, fields, models


class TrialBalancePrefix(models.Model):
    """Reusable account-code prefix (e.g. ``10``, ``4``, ``6011``).

    The wizard's *Accounts* field is a ``many2many_tags`` on this model: users type several
    prefixes and the report keeps every account whose code starts with any of them.
    Prefixes are stored once and reused across reports.
    """

    _name = "dynamic.trial.balance.prefix"
    _description = "Trial Balance Account Prefix"
    _order = "name"

    name = fields.Char(required=True)

    _name_uniq = models.Constraint("UNIQUE(name)", "This account prefix already exists.")

    @api.model_create_multi
    def create(self, vals_list):
        """Strip surrounding spaces so that ``" 10"`` and ``"10"`` are the same prefix."""
        for vals in vals_list:
            if vals.get("name"):
                vals["name"] = vals["name"].strip()
        return super().create(vals_list)

    @api.model
    def name_create(self, name):
        """Reuse an existing prefix instead of failing on the unique constraint.

        Called by the tags widget when the user types a value and presses Enter.
        """
        existing = self.search([("name", "=", name.strip())], limit=1)
        if existing:
            return existing.id, existing.display_name
        return super().name_create(name)
