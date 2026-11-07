"""Calculation tests of the Dynamic Trial Balance against a known dataset.

Dataset (company currency, fiscal year = calendar year, report period = February 2024):

=====  ==========  =========  ==================================================
Entry  Date        State      Lines
=====  ==========  =========  ==================================================
M1     2023-12-15  posted     881101 D100 / 888801 (income) C100
M2     2024-01-10  posted     881101 D50  / 888801 C50
M3     2024-02-10  posted     881102 D30 (analytic A) / 881101 C30
M4     2024-02-12  posted     881102 D60 (EUR 120) / 888801 C60 (EUR -120) — 2nd journal
M5     2024-02-15  draft      881201 D20  / 888801 C20
M6     2024-02-20  cancelled  881201 D1000 / 888801 C1000
=====  ==========  =========  ==================================================

Account groups: 88 > 881 > 8811 (881101, 881102) and 881 > 8812 (881201); 8888 (888801).
"""

import io

from odoo import Command
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

PERIOD = {"date_from": "2024-02-01", "date_to": "2024-02-29"}


@tagged("post_install", "-at_install")
class TestDynamicTrialBalance(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = cls.env["dynamic.trial.balance.engine"]
        cls.eur = cls.setup_other_currency("EUR") if cls.env.company.currency_id.name != "EUR" \
            else cls.setup_other_currency("USD")

        Group = cls.env["account.group"]
        cls.group_88 = Group.create({"name": "Test Root", "code_prefix_start": "88"})
        cls.group_881 = Group.create({"name": "Test Assets", "code_prefix_start": "881"})
        cls.group_8811 = Group.create({"name": "Test Cash", "code_prefix_start": "8811"})
        cls.group_8812 = Group.create({"name": "Test Receivables", "code_prefix_start": "8812"})
        cls.group_8888 = Group.create({"name": "Test Income", "code_prefix_start": "8888"})

        Account = cls.env["account.account"]
        cls.acc_cash1 = Account.create({"code": "881101", "name": "Cash 1", "account_type": "asset_current"})
        cls.acc_cash2 = Account.create({"code": "881102", "name": "Cash 2", "account_type": "asset_current"})
        cls.acc_other = Account.create({"code": "881201", "name": "Other Asset", "account_type": "asset_current"})
        cls.acc_income = Account.create({"code": "888801", "name": "Test Income", "account_type": "income"})

        cls.plan = cls.env["account.analytic.plan"].create({"name": "TB Plan"})
        cls.analytic_a = cls.env["account.analytic.account"].create({"name": "Analytic A", "plan_id": cls.plan.id})

        cls.journal = cls.company_data["default_journal_misc"]
        cls.journal_2 = cls.journal.copy({"name": "Misc 2", "code": "MISC2"})

        cls.m1 = cls._entry("2023-12-15", [(cls.acc_cash1, 100), (cls.acc_income, -100)])
        cls.m2 = cls._entry("2024-01-10", [(cls.acc_cash1, 50), (cls.acc_income, -50)])
        cls.m3 = cls._entry("2024-02-10", [
            (cls.acc_cash2, 30, {"analytic_distribution": {str(cls.analytic_a.id): 100}}),
            (cls.acc_cash1, -30),
        ])
        cls.m4 = cls._entry("2024-02-12", [
            (cls.acc_cash2, 60, {"currency_id": cls.eur.id, "amount_currency": 120}),
            (cls.acc_income, -60, {"currency_id": cls.eur.id, "amount_currency": -120}),
        ], journal=cls.journal_2)
        cls.m5 = cls._entry("2024-02-15", [(cls.acc_other, 20), (cls.acc_income, -20)], post=False)
        cls.m6 = cls._entry("2024-02-20", [(cls.acc_other, 1000), (cls.acc_income, -1000)], post=False)
        cls.m6.button_cancel()

    @classmethod
    def _entry(cls, date, lines, journal=None, post=True):
        move = cls.env["account.move"].create({
            "move_type": "entry",
            "date": date,
            "journal_id": (journal or cls.journal).id,
            "line_ids": [
                Command.create({
                    "account_id": line[0].id,
                    "name": "/",
                    "debit": max(line[1], 0.0),
                    "credit": max(-line[1], 0.0),
                    **(line[2] if len(line) > 2 else {}),
                })
                for line in lines
            ],
        })
        if post:
            move.action_post()
        return move

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _report(self, **options):
        return self.engine.get_report_data({**PERIOD, "account_prefixes": ["88"], **options})

    def _line(self, report, account):
        lines = [line for line in report["lines"] if line.get("account_id") == account.id]
        self.assertEqual(len(lines), 1, f"Expected one line for {account.code}")
        return lines[0]

    def _assert_amounts(self, line, expected):
        keys = ("initial_debit", "initial_credit", "initial_balance",
                "period_debit", "period_credit", "period_balance",
                "end_debit", "end_credit", "end_balance")
        self.assertEqual({key: line[key] for key in keys}, dict(zip(keys, expected)))

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_posted_figures(self):
        report = self._report()
        #                                              initial         movement        end
        self._assert_amounts(self._line(report, self.acc_cash1), (150, 0, 150, 0, 30, -30, 120, 0, 120))
        self._assert_amounts(self._line(report, self.acc_cash2), (0, 0, 0, 90, 0, 90, 90, 0, 90))
        self._assert_amounts(self._line(report, self.acc_other), (0, 0, 0, 0, 0, 0, 0, 0, 0))
        # P&L account: only the current fiscal year is brought forward (M1 of 2023 is excluded).
        self._assert_amounts(self._line(report, self.acc_income), (0, 50, -50, 0, 60, -60, 0, 110, -110))
        total = report["total"]
        self.assertEqual(total["period_debit"], total["period_credit"])
        # Filtered on "88" the previous-year result (on the unaffected earnings account) is
        # outside the selection, so only the period movements balance here.
        self.assertEqual(total["end_balance"], 100.0)

    def test_full_report_balances(self):
        """Without account filter every section of the grand total nets to zero."""
        total = self.engine.get_report_data({**PERIOD, "include_unposted": True})["total"]
        for section in ("initial", "period", "end"):
            self.assertEqual(total[f"{section}_debit"], total[f"{section}_credit"], section)
            self.assertEqual(total[f"{section}_balance"], 0.0, section)

    def test_previous_years_result_on_unaffected_earnings(self):
        unaffected = self.env.company.get_unaffected_earnings_account()
        report = self.engine.get_report_data({**PERIOD, "account_prefixes": [unaffected.code]})
        self.assertEqual(self._line(report, unaffected)["initial_balance"], -100)

    def test_unposted_entries(self):
        report = self._report(include_unposted=True)
        self._assert_amounts(self._line(report, self.acc_other), (0, 0, 0, 20, 0, 20, 20, 0, 20))
        # The cancelled entry M6 is never included.
        self.assertEqual(self._line(report, self.acc_income)["period_credit"], 80)

    def test_account_prefix_filter(self):
        report = self._report(account_prefixes=["8811", "8888"])
        self.assertEqual(
            {line["code"] for line in report["lines"]},
            {"881101", "881102", "888801"},
        )
        # LIKE wildcards typed by the user are matched literally
        report = self._report(account_prefixes=["88_1"])
        self.assertFalse(report["lines"])

    def test_journal_filter(self):
        report = self._report(journal_ids=[self.journal_2.id])
        self.assertEqual(self._line(report, self.acc_cash2)["period_debit"], 60)
        self.assertEqual(self._line(report, self.acc_cash1)["initial_balance"], 0)

    def test_analytic_filter(self):
        report = self._report(analytic_account_ids=[self.analytic_a.id], skip_zero_balance=True)
        self.assertEqual([line["code"] for line in report["lines"]], ["881102"])
        self.assertEqual(report["lines"][0]["period_debit"], 30)

    def test_skip_zero_balance(self):
        report = self._report(skip_zero_balance=True)
        self.assertNotIn(self.acc_other.id, [line.get("account_id") for line in report["lines"]])
        self.assertIn(self.acc_cash1.id, [line.get("account_id") for line in report["lines"]])

    def test_hierarchy_subtotals(self):
        report = self._report(hierarchy=True)
        codes = [line["code"] for line in report["lines"]]
        self.assertEqual(codes, ["88", "881", "8811", "881101", "881102", "8812", "881201", "8888", "888801"])
        by_code = {line["code"]: line for line in report["lines"]}
        self.assertEqual(by_code["8811"]["end_balance"], 210)
        self.assertEqual(by_code["881"]["period_debit"], 90)
        self.assertEqual(by_code["88"]["end_balance"], 100)
        self.assertEqual(by_code["88"]["level"], 1)
        self.assertEqual(by_code["8811"]["level"], 3)
        self.assertEqual(by_code["881101"]["level"], 4)
        self.assertEqual(by_code["881101"]["parent_id"], f"group-{self.group_8811.id}")

    def test_hierarchy_only_parents(self):
        report = self._report(only_parents=True, account_level=2)
        self.assertEqual([line["code"] for line in report["lines"]], ["88", "881", "8888"])
        self.assertTrue(all(line["type"] == "group" for line in report["lines"]))

    def test_amount_currency_breakdown(self):
        report = self._report(show_amount_currency=True)
        cash2_lines = [line for line in report["lines"] if line.get("account_id") == self.acc_cash2.id]
        by_currency = {line["currency"]["name"]: line for line in cash2_lines}
        company_currency = self.env.company.currency_id.name
        self.assertEqual(set(by_currency), {company_currency, self.eur.name})
        self.assertEqual(by_currency[self.eur.name]["amount_currency"], 120)
        self.assertEqual(by_currency[self.eur.name]["period_debit"], 60)
        self.assertEqual(by_currency[company_currency]["period_debit"], 30)

    def test_access_accounting_administrator(self):
        """In Odoo 19 the accounting Administrator group does not imply Read-only:
        such a user must still be able to run the report."""
        user = new_test_user(
            self.env, login="dtb_manager", groups="base.group_user,account.group_account_manager",
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)],
        )
        self.assertFalse(user.has_group("account.group_account_readonly"))
        wizard = self.env["dynamic.trial.balance.wizard"].with_user(user).create(PERIOD)
        self.assertTrue(wizard.get_report_data()["lines"])

    def test_invalid_period(self):
        with self.assertRaises(Exception):
            self.engine.get_report_data({"date_from": "2024-03-01", "date_to": "2024-02-01"})

    def test_wizard_outputs(self):
        prefix = self.env["dynamic.trial.balance.prefix"].name_create("88")[0]
        wizard = self.env["dynamic.trial.balance.wizard"].create({
            **PERIOD,
            "hierarchy": True,
            "account_prefix_ids": [Command.set([prefix])],
        })
        self.assertEqual(wizard.action_preview()["params"]["options"]["account_prefixes"], ["88"])

        pdf_content, report_type = self.env["ir.actions.report"]._render_qweb_html(
            "account_dynamic_trial_balance.action_report_trial_balance", wizard.ids
        )
        self.assertEqual(report_type, "html")
        self.assertIn(b"881101", pdf_content)

        xlsx = wizard._generate_xlsx()
        self.assertTrue(xlsx.startswith(b"PK"), "XLSX output must be a zip archive")
        from openpyxl import load_workbook  # noqa: PLC0415 - optional, only for the test
        sheet = load_workbook(io.BytesIO(xlsx)).active
        values = [cell for row in sheet.iter_rows(values_only=True) for cell in row]
        self.assertIn("881101", values)
