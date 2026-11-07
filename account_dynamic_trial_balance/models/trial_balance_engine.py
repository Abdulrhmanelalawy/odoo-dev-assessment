"""Calculation engine of the Dynamic Trial Balance.

The engine is a stateless AbstractModel: ``get_report_data(options)`` takes a plain,
JSON-serialisable ``options`` dict (built by the wizard or by the on-screen preview) and
returns the report lines. PDF, XLSX and the preview all render the very same structure,
so the figures can never diverge between outputs.

All amounts are aggregated in SQL through ``_read_group`` (one GROUP BY query per period),
which keeps record rules / multi-company security and scales with the number of journal
items.
"""

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import escape_psql

# The nine figures carried by every report line (account, group subtotal and grand total).
AMOUNT_KEYS = (
    "initial_debit", "initial_credit", "initial_balance",
    "period_debit", "period_credit", "period_balance",
    "end_debit", "end_credit", "end_balance",
)

# Deepest account-group level selectable with "Hierarchy Only Parents".
MAX_ACCOUNT_LEVEL = 5


class TrialBalanceEngine(models.AbstractModel):
    _name = "dynamic.trial.balance.engine"
    _description = "Dynamic Trial Balance Engine"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @api.model
    def get_report_data(self, options):
        """Compute the trial balance.

        :param dict options: see ``_sanitize_options`` for the accepted keys.
        :return: dict with ``header`` (company, period, applied filters), ``lines``
            (ordered list of group/account line dicts) and ``total`` (grand total line).
        """
        options = self._sanitize_options(options)
        company = self.env.company
        accounts = self._get_accounts(options)
        amounts = self._compute_amounts(options, accounts)
        account_lines = self._build_account_lines(options, accounts, amounts)

        if options["skip_zero_balance"]:
            account_lines = [line for line in account_lines if not self._is_zero_line(line)]

        if options["hierarchy"]:
            lines = self._build_hierarchy(options, account_lines)
        else:
            lines = account_lines

        return {
            "header": self._get_header(options),
            "options": options,
            "lines": lines,
            "total": self._build_total_line(account_lines),
            "company_currency": self._currency_info(company.currency_id),
        }

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    @api.model
    def _sanitize_options(self, options):
        """Validate and normalize the report options.

        Accepted keys (all optional except the dates):

        * ``date_from`` / ``date_to`` (str ``YYYY-MM-DD``): reporting period.
        * ``include_unposted`` (bool): report draft entries next to posted ones.
        * ``hierarchy`` (bool): group accounts by ``account.group`` with subtotals.
        * ``only_parents`` (bool) + ``account_level`` (1-5): keep group lines only, down
          to the given level.
        * ``account_prefixes`` (list[str]): keep accounts whose code starts with any prefix.
        * ``journal_ids`` / ``analytic_account_ids`` (list[int]): journal-item filters.
        * ``skip_zero_balance`` (bool): hide accounts without balance nor movement.
        * ``show_amount_currency`` (bool): one line per account and transaction currency.

        :return: a new dict containing every key above with a well-typed value.
        :raise UserError: when a date is missing or the period is inverted.
        """
        options = dict(options or {})
        date_from = fields.Date.to_date(options.get("date_from"))
        date_to = fields.Date.to_date(options.get("date_to"))
        if not date_from or not date_to:
            raise UserError(_("Both a start date and an end date are required."))
        if date_from > date_to:
            raise UserError(_("The start date must be before the end date."))

        only_parents = bool(options.get("only_parents"))
        level = int(options.get("account_level") or 1)
        return {
            "date_from": fields.Date.to_string(date_from),
            "date_to": fields.Date.to_string(date_to),
            "include_unposted": bool(options.get("include_unposted")),
            # "Hierarchy Only Parents" is a hierarchy view by definition.
            "hierarchy": bool(options.get("hierarchy")) or only_parents,
            "only_parents": only_parents,
            "account_level": min(max(level, 1), MAX_ACCOUNT_LEVEL),
            "account_prefixes": [p.strip() for p in options.get("account_prefixes") or [] if p and p.strip()],
            "journal_ids": [int(i) for i in options.get("journal_ids") or []],
            "analytic_account_ids": [int(i) for i in options.get("analytic_account_ids") or []],
            "skip_zero_balance": bool(options.get("skip_zero_balance")),
            "show_amount_currency": bool(options.get("show_amount_currency")),
        }

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    @api.model
    def _get_accounts(self, options):
        """Accounts of the current company, restricted by the code prefixes (OR-ed)."""
        domain = Domain(self.env["account.account"]._check_company_domain(self.env.company))
        if options["account_prefixes"]:
            # escape LIKE wildcards: a prefix is matched literally
            domain &= Domain.OR(
                Domain("code", "=like", escape_psql(prefix) + "%") for prefix in options["account_prefixes"]
            )
        return self.env["account.account"].search(domain)

    @api.model
    def _base_move_line_domain(self, options):
        """Journal-item domain shared by every query: company, entry state, journals, analytics.

        The analytic filter relies on the ``analytic_distribution`` search of ``analytic.mixin``,
        which matches items whose distribution contains any of the given analytic accounts.
        """
        states = ["posted", "draft"] if options["include_unposted"] else ["posted"]
        domain = Domain([
            ("company_id", "=", self.env.company.id),
            ("parent_state", "in", states),  # cancelled entries are never reported
            ("display_type", "not in", ("line_section", "line_note")),
        ])
        if options["journal_ids"]:
            domain &= Domain("journal_id", "in", options["journal_ids"])
        if options["analytic_account_ids"]:
            domain &= Domain("analytic_distribution", "in", options["analytic_account_ids"])
        return domain

    @api.model
    def _compute_amounts(self, options, accounts):
        """Return ``{(account_id, currency_id or False): {"initial": {...}, "period": {...}}}``.

        * initial: balance-sheet accounts carry everything before ``date_from``; P&L accounts
          (``include_initial_balance = False``) only carry the current fiscal year, the previous
          years' result being reported on the "current year earnings" account — same rule as
          Odoo's own trial balance.
        * period: journal items between ``date_from`` and ``date_to``.
        """
        result = defaultdict(lambda: {"initial": _empty_bucket(), "period": _empty_bucket()})
        if not accounts:
            return result

        company = self.env.company
        date_from = fields.Date.to_date(options["date_from"])
        fy_start = company.compute_fiscalyear_dates(date_from)["date_from"]
        base = self._base_move_line_domain(options)
        on_accounts = base & Domain("account_id", "in", accounts.ids)

        period_domain = on_accounts & Domain([
            ("date", ">=", options["date_from"]),
            ("date", "<=", options["date_to"]),
        ])
        initial_domain = on_accounts & Domain("date", "<", options["date_from"]) & (
            Domain("account_id.include_initial_balance", "=", True)
            | Domain("date", ">=", fy_start)
        )
        self._accumulate(result, "period", period_domain, options)
        self._accumulate(result, "initial", initial_domain, options)

        # Result of the previous fiscal years: P&L accounts were reset above, so their
        # cumulated balance is brought forward on the "current year earnings" account.
        unaffected = self.env["account.account"].search([
            *self.env["account.account"]._check_company_domain(company),
            ("account_type", "=", "equity_unaffected"),
        ], limit=1)
        if unaffected and unaffected in accounts:
            previous_years_result = base & Domain([
                ("date", "<", fy_start),
                ("account_id.include_initial_balance", "=", False),
            ])
            self._accumulate(result, "initial", previous_years_result, options, force_account=unaffected)
        return result

    @api.model
    def _accumulate(self, result, bucket, domain, options, force_account=None):
        """Add the sums of the journal items matching ``domain`` into ``result``.

        :param dict result: accumulator returned by ``_compute_amounts`` (mutated in place).
        :param str bucket: ``"initial"`` or ``"period"``.
        :param Domain domain: journal items to aggregate.
        :param dict options: sanitized options (``show_amount_currency`` adds a currency key).
        :param force_account: book every row on this account instead of the item's own
            account (used for the previous years' result).
        """
        groupby = ["account_id"]
        if options["show_amount_currency"]:
            groupby.append("currency_id")
        rows = self.env["account.move.line"]._read_group(
            domain,
            groupby=groupby,
            aggregates=["debit:sum", "credit:sum", "balance:sum", "amount_currency:sum"],
        )
        for row in rows:
            account = force_account or row[0]
            currency = row[1] if options["show_amount_currency"] else None
            debit, credit, balance, amount_currency = row[-4:]
            key = (account.id, currency.id if currency else False)
            target = result[key][bucket]
            target["debit"] += debit
            target["credit"] += credit
            target["balance"] += balance
            target["amount_currency"] += amount_currency

    # ------------------------------------------------------------------
    # Lines
    # ------------------------------------------------------------------

    @api.model
    def _build_account_lines(self, options, accounts, amounts):
        """One line per account (or per account and currency), ordered by account code.

        Accounts without any journal item still get a zero line, so that the report lists the
        whole chart of accounts unless ``skip_zero_balance`` is set.
        """
        company_currency = self.env.company.currency_id
        keys_by_account = defaultdict(list)
        for account_id, currency_id in amounts:
            keys_by_account[account_id].append(currency_id)

        currencies = self.env["res.currency"].browse(
            {currency_id for _account, currency_id in amounts if currency_id}
        )
        currency_by_id = {currency.id: currency for currency in currencies}

        lines = []
        for account in accounts.sorted(lambda a: (a.code or "", a.id)):
            currency_ids = keys_by_account.get(account.id) or [
                company_currency.id if options["show_amount_currency"] else False
            ]
            # company currency first, then the foreign currencies
            for currency_id in sorted(currency_ids, key=lambda cid: (cid != company_currency.id, cid or 0)):
                buckets = amounts.get((account.id, currency_id)) or {
                    "initial": _empty_bucket(), "period": _empty_bucket(),
                }
                line = {
                    "id": f"account-{account.id}" + (f"-{currency_id}" if currency_id else ""),
                    "type": "account",
                    "account_id": account.id,
                    "group_id": account.group_id.id or False,
                    "code": account.code or "",
                    "name": account.name,
                    "level": 1,
                    "parent_id": False,
                    **self._amount_columns(buckets["initial"], buckets["period"]),
                }
                if options["show_amount_currency"]:
                    currency = currency_by_id.get(currency_id) or company_currency
                    line["currency"] = self._currency_info(currency)
                    line["amount_currency"] = currency.round(
                        buckets["initial"]["amount_currency"] + buckets["period"]["amount_currency"]
                    )
                lines.append(line)
        return lines

    @api.model
    def _amount_columns(self, initial, period):
        """Initial / End are shown as a net position (debit OR credit), the period as gross
        movements, which is how Odoo's trial balance presents them."""
        rnd = self.env.company.currency_id.round
        initial_balance = rnd(initial["balance"])
        period_balance = rnd(period["balance"])
        end_balance = rnd(initial_balance + period_balance)
        return {
            "initial_debit": max(initial_balance, 0.0),
            "initial_credit": max(-initial_balance, 0.0),
            "initial_balance": initial_balance,
            "period_debit": rnd(period["debit"]),
            "period_credit": rnd(period["credit"]),
            "period_balance": period_balance,
            "end_debit": max(end_balance, 0.0),
            "end_credit": max(-end_balance, 0.0),
            "end_balance": end_balance,
        }

    @api.model
    def _is_zero_line(self, line):
        """True when the line has no initial balance, no movement and no ending balance.

        Debit and credit are checked separately: a period with equal debits and credits has a
        zero net movement but still has transactions, so the account is kept.
        """
        is_zero = self.env.company.currency_id.is_zero
        return all(
            is_zero(line[key])
            for key in ("initial_balance", "period_debit", "period_credit", "end_balance")
        )

    @api.model
    def _build_hierarchy(self, options, account_lines):
        """Insert ``account.group`` subtotal lines and order everything depth-first.

        Only the groups containing at least one reported account (and their ancestors) are
        shown. Accounts without a group stay at the root level. With ``only_parents``, the
        account lines are dropped and groups deeper than ``account_level`` are cut off.
        """
        # 1. collect the groups of the reported accounts and all their ancestors
        groups = self.env["account.group"].browse({line["group_id"] for line in account_lines if line["group_id"]})
        all_groups = groups
        for group in groups:
            parent = group.parent_id
            while parent:
                all_groups |= parent
                parent = parent.parent_id

        def depth(group):
            level, parent = 1, group.parent_id
            while parent:
                level, parent = level + 1, parent.parent_id
            return level

        # 2. one subtotal line per group, amounts filled in step 3
        group_lines = {}
        for group in all_groups:
            code = group.code_prefix_start or ""
            if group.code_prefix_end and group.code_prefix_end != group.code_prefix_start:
                code = f"{code}-{group.code_prefix_end}"
            group_lines[group.id] = {
                "id": f"group-{group.id}",
                "type": "group",
                "group_id": group.id,
                "code": code,
                "sort_key": group.code_prefix_start or "",
                "name": group.name,
                "level": depth(group),
                "parent_id": f"group-{group.parent_id.id}" if group.parent_id else False,
                **{key: 0.0 for key in AMOUNT_KEYS},
            }

        children = defaultdict(list)  # parent line id (False = root) -> child lines
        for group_line in group_lines.values():
            children[group_line["parent_id"]].append(group_line)

        # 3. attach each account to its group and add its amounts to every ancestor
        group_by_id = {group.id: group for group in all_groups}
        for line in account_lines:
            group = group_by_id.get(line["group_id"])
            if group:
                line["parent_id"] = f"group-{group.id}"
                line["level"] = group_lines[group.id]["level"] + 1
                while group:
                    subtotal = group_lines[group.id]
                    for key in AMOUNT_KEYS:
                        subtotal[key] += line[key]
                    group = group.parent_id
            children[line["parent_id"]].append(line)

        rnd = self.env.company.currency_id.round
        for subtotal in group_lines.values():
            for key in AMOUNT_KEYS:
                subtotal[key] = rnd(subtotal[key])

        # 4. depth-first ordering: a group is followed by its sub-groups and accounts by code
        ordered = []

        def walk(parent_id):
            for node in sorted(children[parent_id], key=lambda n: (n.get("sort_key", n["code"]), n["type"] != "group", n["id"])):
                ordered.append(node)
                if node["type"] == "group":
                    walk(node["id"])

        walk(False)
        for node in ordered:
            node.pop("sort_key", None)

        if options["only_parents"]:
            ordered = [
                line for line in ordered
                if line["type"] == "group" and line["level"] <= options["account_level"]
            ]
        return ordered

    @api.model
    def _build_total_line(self, account_lines):
        """Grand total, computed on account lines only (group subtotals would double count)."""
        rnd = self.env.company.currency_id.round
        total = {
            "id": "total",
            "type": "total",
            "code": "",
            "name": _("Total"),
            "level": 0,
            "parent_id": False,
        }
        for key in AMOUNT_KEYS:
            total[key] = rnd(sum(line[key] for line in account_lines))
        return total

    # ------------------------------------------------------------------
    # Header helpers
    # ------------------------------------------------------------------

    @api.model
    def _currency_info(self, currency):
        """JSON-friendly currency description used by the preview and the XLSX formats."""
        return {
            "id": currency.id,
            "name": currency.name,
            "symbol": currency.symbol,
            "position": currency.position,
            "decimal_places": currency.decimal_places,
        }

    @api.model
    def _get_header(self, options):
        """Report heading: company, period and a human-readable list of the active filters."""
        company = self.env.company
        filters = []
        if options["include_unposted"]:
            filters.append(_("Including unposted entries"))
        if options["account_prefixes"]:
            filters.append(_("Accounts: %s", ", ".join(options["account_prefixes"])))
        if options["journal_ids"]:
            journals = self.env["account.journal"].browse(options["journal_ids"])
            filters.append(_("Journals: %s", ", ".join(journals.mapped("code"))))
        if options["analytic_account_ids"]:
            analytics = self.env["account.analytic.account"].browse(options["analytic_account_ids"])
            filters.append(_("Analytic: %s", ", ".join(analytics.mapped("display_name"))))
        if options["only_parents"]:
            filters.append(_("Hierarchy up to level %s", options["account_level"]))
        elif options["hierarchy"]:
            filters.append(_("Hierarchy and subtotals"))
        if options["skip_zero_balance"]:
            filters.append(_("Zero balances hidden"))
        if options["show_amount_currency"]:
            filters.append(_("By transaction currency"))
        return {
            "company_name": company.name,
            "date_from": options["date_from"],
            "date_to": options["date_to"],
            "filters": filters,
        }


def _empty_bucket():
    """Zeroed accumulator for one account / currency / section."""
    return {"debit": 0.0, "credit": 0.0, "balance": 0.0, "amount_currency": 0.0}
