"""Demo data for the Dynamic Trial Balance.

Generated in Python rather than XML because account codes are company dependent and the
entries must use the accounts of whatever chart of accounts the demo company runs.
Everything is idempotent: re-running the loader does nothing once the demo exists.
"""

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models

TOP_LEVEL_NAMES = {
    "1": "Assets",
    "2": "Liabilities",
    "3": "Equity",
    "4": "Income",
    "5": "Cost of Revenue",
    "6": "Expenses",
    "7": "Other Income",
    "8": "Other Expenses",
    "9": "Closing & Other",
}
DEMO_REF_PREFIX = "DTB-DEMO"


class TrialBalanceEngine(models.AbstractModel):
    _inherit = "dynamic.trial.balance.engine"

    @api.model
    def _load_demo_data(self):
        company = self.env.company
        Account = self.env["account.account"].with_company(company)
        if not Account.search_count(Account._check_company_domain(company), limit=1):
            return  # no chart of accounts installed: nothing to attach the demo to
        if self.env["account.move"].search_count([("ref", "=like", f"{DEMO_REF_PREFIX}%")], limit=1):
            return
        self._demo_account_groups(company)
        self._demo_journal_entries(company)

    @api.model
    def _demo_account_groups(self, company):
        """Build a 4-level account group tree (1 / 10 / 101 / 1010) from existing codes."""
        Group = self.env["account.group"]
        if Group.search_count([("company_id", "=", company.root_id.id)], limit=1):
            return  # the localisation already ships account groups
        Account = self.env["account.account"].with_company(company)
        codes = [code for code in Account.search(Account._check_company_domain(company)).mapped("code") if code]
        prefixes = sorted({code[:length] for code in codes for length in range(1, 5) if len(code) > length})
        for prefix in prefixes:
            if len(prefix) == 1:
                name = TOP_LEVEL_NAMES.get(prefix, f"Class {prefix}")
            else:
                sample = Account.search([("code", "=like", f"{prefix}%")], limit=1, order="code")
                name = f"{prefix} - {sample.name}" if sample else f"Group {prefix}"
            Group.create({"name": name, "code_prefix_start": prefix, "company_id": company.root_id.id})

    @api.model
    def _demo_journal_entries(self, company):
        Account = self.env["account.account"].with_company(company)

        def account(account_type):
            return Account.search([*Account._check_company_domain(company), ("account_type", "=", account_type)], limit=1)

        bank = account("asset_cash")
        receivable = account("asset_receivable")
        payable = account("liability_payable")
        income = account("income")
        expense = account("expense")
        if not all((bank, receivable, payable, income, expense)):
            return

        journal = self.env["account.journal"].search([
            *self.env["account.journal"]._check_company_domain(company), ("type", "=", "general"),
        ], limit=1)
        foreign = self.env.ref("base.EUR") if company.currency_id != self.env.ref("base.EUR") else self.env.ref("base.USD")
        foreign.active = True
        if not foreign.rate_ids.filtered(lambda r: r.company_id == company):
            self.env["res.currency.rate"].create({
                "currency_id": foreign.id, "company_id": company.id,
                "name": fields.Date.to_string(fields.Date.today() - relativedelta(years=2)), "rate": 0.9,
            })

        plan = self.env["account.analytic.plan"].search([("name", "=", "Departments")], limit=1) \
            or self.env["account.analytic.plan"].create({"name": "Departments"})
        analytic_sales, analytic_admin = (
            self.env["account.analytic.account"].search([("name", "=", name), ("plan_id", "=", plan.id)], limit=1)
            or self.env["account.analytic.account"].create({"name": name, "plan_id": plan.id})
            for name in ("Sales", "Administration")
        )

        today = fields.Date.today()
        month_start = today.replace(day=1)

        def this_month(day_offset):
            # keep "current month" entries inside the wizard's default period (1st -> today)
            return min(month_start + relativedelta(days=day_offset), today)

        entries = [
            # (date, state, lines[(account, amount, extra)])
            (month_start - relativedelta(years=1, months=1), "posted", [(bank, 5000), (income, -5000)]),
            (month_start - relativedelta(years=1), "posted", [(expense, 1200, {"analytic_distribution": {str(analytic_admin.id): 100}}), (payable, -1200)]),
            (month_start - relativedelta(months=2), "posted", [(receivable, 3000), (income, -3000, {"analytic_distribution": {str(analytic_sales.id): 100}})]),
            (month_start - relativedelta(months=1), "posted", [(bank, 2500), (receivable, -2500)]),
            (this_month(2), "posted", [(expense, 800, {"analytic_distribution": {str(analytic_admin.id): 60, str(analytic_sales.id): 40}}), (bank, -800)]),
            (this_month(5), "posted", [
                (bank, 900, {"currency_id": foreign.id, "amount_currency": 810}),
                (income, -900, {"currency_id": foreign.id, "amount_currency": -810, "analytic_distribution": {str(analytic_sales.id): 100}}),
            ]),
            (this_month(8), "draft", [(receivable, 1500), (income, -1500)]),
            (this_month(10), "cancel", [(expense, 9999), (bank, -9999)]),
        ]
        for index, (date, state, lines) in enumerate(entries, start=1):
            move = self.env["account.move"].create({
                "move_type": "entry",
                "ref": f"{DEMO_REF_PREFIX}-{index:02d}",
                "date": date,
                "journal_id": journal.id,
                "line_ids": [
                    Command.create({
                        "account_id": line[0].id,
                        "name": f"Demo {index}",
                        "debit": max(line[1], 0.0),
                        "credit": max(-line[1], 0.0),
                        **(line[2] if len(line) > 2 else {}),
                    })
                    for line in lines
                ],
            })
            if state == "posted":
                move.action_post()
            elif state == "cancel":
                move.button_cancel()
