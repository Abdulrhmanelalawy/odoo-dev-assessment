"""Dynamic Trial Balance wizard: report options and the three outputs (preview, PDF, XLSX)."""

import io

import xlsxwriter

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import start_of


class TrialBalanceWizard(models.TransientModel):
    """Collects the report options and dispatches them to the selected output.

    The wizard holds no computation: it converts its fields into the options dict expected by
    ``dynamic.trial.balance.engine`` (see ``_get_report_options``) so that the on-screen
    preview, the PDF and the XLSX file always show the same figures.
    """

    _name = "dynamic.trial.balance.wizard"
    _description = "Dynamic Trial Balance"

    company_id = fields.Many2one("res.company", required=True, readonly=True, default=lambda self: self.env.company)
    date_from = fields.Date(string="Start Date", required=True, default=lambda self: start_of(fields.Date.context_today(self), "month"))
    date_to = fields.Date(string="End Date", required=True, default=fields.Date.context_today)

    include_unposted = fields.Boolean(
        string="Include Unposted Entries",
        help="Draft journal entries are reported together with the posted ones. Cancelled entries are never reported.",
    )
    hierarchy = fields.Boolean(
        string="Hierarchy and Subtotals",
        help="Group the accounts by account group and display a subtotal for each group.",
    )
    only_parents = fields.Boolean(
        string="Hierarchy Only Parents",
        help="Only display the account groups, down to the selected level.",
    )
    account_level = fields.Selection(
        [(str(level), str(level)) for level in range(1, 6)],
        string="Account Level Up To",
        default="1",
    )
    account_prefix_ids = fields.Many2many(
        "dynamic.trial.balance.prefix",
        string="Accounts",
        help="Specify the account prefix to view only matching accounts. If no prefix is entered, all accounts will be displayed.",
    )
    journal_ids = fields.Many2many(
        "account.journal",
        string="Journals",
        domain="[('company_id', 'parent_of', company_id)]",
        help="Select specific journals to include in the report, or leave the field empty to include all journals.",
    )
    analytic_account_ids = fields.Many2many(
        "account.analytic.account",
        string="Analytic Accounts",
        help="Select specific analytic accounts to include in the report, or leave the field empty to include all.",
    )
    skip_zero_balance = fields.Boolean(
        string="Skip Zero Balance",
        help="Select this option to hide accounts that have neither an initial balance nor any transactions in this report.",
    )
    show_amount_currency = fields.Boolean(
        string="Show Amount Currency",
        help="Enable this option to group the report by Account, followed by Amount Currency. This will show the sum "
             "of the Amount Currency for each account in its respective currency. Essentially, this option provides "
             "a breakdown of account balances by the transaction currency used.",
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(_("The start date must be before the end date."))

    # ------------------------------------------------------------------
    # Options <-> wizard
    # ------------------------------------------------------------------

    def _get_report_options(self):
        """Convert the wizard fields into the engine's JSON-serializable options dict."""
        self.ensure_one()
        return {
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "include_unposted": self.include_unposted,
            "hierarchy": self.hierarchy,
            "only_parents": self.only_parents,
            "account_level": int(self.account_level or 1),
            "account_prefixes": self.account_prefix_ids.mapped("name"),
            "journal_ids": self.journal_ids.ids,
            "analytic_account_ids": self.analytic_account_ids.ids,
            "skip_zero_balance": self.skip_zero_balance,
            "show_amount_currency": self.show_amount_currency,
        }

    @api.model
    def create_from_options(self, options):
        """Create a wizard from an options dict and return its id.

        Used by the on-screen preview: its PDF / XLSX buttons export exactly the options
        currently displayed, which may differ from the wizard that opened the preview.
        """
        options = self.env["dynamic.trial.balance.engine"]._sanitize_options(options)
        Prefix = self.env["dynamic.trial.balance.prefix"]
        prefixes = Prefix.browse([Prefix.name_create(name)[0] for name in options["account_prefixes"]])
        wizard = self.create({
            "date_from": options["date_from"],
            "date_to": options["date_to"],
            "include_unposted": options["include_unposted"],
            "hierarchy": options["hierarchy"],
            "only_parents": options["only_parents"],
            "account_level": str(options["account_level"]),
            "account_prefix_ids": [fields.Command.set(prefixes.ids)],
            "journal_ids": [fields.Command.set(options["journal_ids"])],
            "analytic_account_ids": [fields.Command.set(options["analytic_account_ids"])],
            "skip_zero_balance": options["skip_zero_balance"],
            "show_amount_currency": options["show_amount_currency"],
        })
        return wizard.id

    def get_report_data(self):
        """Report lines for this wizard, computed in the wizard's company."""
        self.ensure_one()
        return self.env["dynamic.trial.balance.engine"].with_company(self.company_id).get_report_data(
            self._get_report_options()
        )

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    def action_preview(self):
        """Open the OWL client action; the options travel in the action params."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "account_dynamic_trial_balance.preview",
            "name": _("Dynamic Trial Balance"),
            "params": {"options": self._get_report_options()},
        }

    def action_pdf(self):
        """Download the QWeb PDF report (see ``report/trial_balance_report.xml``)."""
        self.ensure_one()
        return self.env.ref("account_dynamic_trial_balance.action_report_trial_balance").report_action(self)

    def _generate_xlsx(self):
        """Build the XLSX file in memory and return its bytes.

        Layout: title rows, a two-level header (section / Debit-Credit-Balance), one row per
        report line with bold group and total rows, Excel outline levels mirroring the account
        hierarchy (collapsible in Excel) and frozen header rows and code/name columns.
        """
        self.ensure_one()
        data = self.get_report_data()
        options = data["options"]
        currency = self.company_id.currency_id
        # zero amounts are left blank, like in the on-screen report
        money_format = "#,##0.{0};-#,##0.{0};\"\"".format("0" * currency.decimal_places) \
            if currency.decimal_places else "#,##0;-#,##0;\"\""

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet(_("Trial Balance")[:31])
        fmt = {
            "title": workbook.add_format({"bold": True, "font_size": 14}),
            "subtitle": workbook.add_format({"italic": True, "font_color": "#666666"}),
            "head": workbook.add_format({"bold": True, "bg_color": "#E9ECEF", "border": 1, "align": "center", "valign": "vcenter"}),
            "text": workbook.add_format({}),
            "money": workbook.add_format({"num_format": money_format}),
            "group_text": workbook.add_format({"bold": True}),
            "group_money": workbook.add_format({"bold": True, "num_format": money_format}),
            "total_text": workbook.add_format({"bold": True, "top": 2}),
            "total_money": workbook.add_format({"bold": True, "top": 2, "num_format": money_format}),
        }

        sheet.write(0, 0, _("Trial Balance"), fmt["title"])
        sheet.write(1, 0, "%s — %s → %s" % (data["header"]["company_name"], options["date_from"], options["date_to"]))
        if data["header"]["filters"]:
            sheet.write(2, 0, " · ".join(data["header"]["filters"]), fmt["subtitle"])

        show_currency = options["show_amount_currency"]
        first_amount_col = 3 if show_currency else 2
        header_row = 4
        sheet.write(header_row + 1, 0, _("Code"), fmt["head"])
        sheet.write(header_row + 1, 1, _("Account"), fmt["head"])
        sheet.merge_range(header_row, 0, header_row, first_amount_col - 1, "", fmt["head"])
        if show_currency:
            sheet.write(header_row + 1, 2, _("Amount Currency"), fmt["head"])
        for index, title in enumerate((_("Initial Balance"), _("Movement"), _("End Balance"))):
            col = first_amount_col + index * 3
            sheet.merge_range(header_row, col, header_row, col + 2, title, fmt["head"])
            for offset, sub_title in enumerate((_("Debit"), _("Credit"), _("Balance"))):
                sheet.write(header_row + 1, col + offset, sub_title, fmt["head"])

        currency_formats = {}

        def currency_format(cur):
            if cur["id"] not in currency_formats:
                decimals = "." + "0" * cur["decimal_places"] if cur["decimal_places"] else ""
                pattern = f'"{cur["symbol"]}" #,##0{decimals}' if cur["position"] == "before" \
                    else f'#,##0{decimals} "{cur["symbol"]}"'
                currency_formats[cur["id"]] = workbook.add_format({"num_format": pattern})
            return currency_formats[cur["id"]]

        row = header_row + 2
        for line in data["lines"] + [data["total"]]:
            kind = {"account": "", "group": "group_", "total": "total_"}[line["type"]]
            text_fmt, money_fmt = fmt[f"{kind}text" if kind else "text"], fmt[f"{kind}money" if kind else "money"]
            sheet.write_string(row, 0, line["code"], text_fmt)
            sheet.write_string(row, 1, line["name"], text_fmt)
            if line["type"] != "total" and options["hierarchy"]:
                # Excel outline levels keep the hierarchy collapsible.
                sheet.set_row(row, None, None, {"level": min(max(line["level"] - 1, 0), 7)})
            if show_currency:
                if line.get("currency"):
                    sheet.write_number(row, 2, line["amount_currency"], currency_format(line["currency"]))
                else:
                    sheet.write_blank(row, 2, None, money_fmt)
            for index, section in enumerate(("initial", "period", "end")):
                col = first_amount_col + index * 3
                for offset, suffix in enumerate(("debit", "credit", "balance")):
                    sheet.write_number(row, col + offset, line[f"{section}_{suffix}"], money_fmt)
            row += 1

        sheet.set_column(0, 0, 14)
        sheet.set_column(1, 1, 42)
        sheet.set_column(2, first_amount_col + 8, 15)
        sheet.freeze_panes(header_row + 2, 2)
        workbook.close()
        return output.getvalue()

    def action_xlsx(self):
        """Download the XLSX file through ``controllers/main.py``."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/account_dynamic_trial_balance/xlsx/{self.id}",
            "target": "download",
        }
