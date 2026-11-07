/* global luxon */
import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

/** sessionStorage key keeping the last options of the tab (survives a page reload). */
const STORAGE_KEY = "account_dynamic_trial_balance.preview_options";

/** The three column sections; each one renders Debit / Credit / Balance. */
const SECTIONS = [
    { key: "initial", label: _t("Initial Balance") },
    { key: "period", label: _t("Movement") },
    { key: "end", label: _t("End Balance") },
];

/**
 * On-screen Dynamic Trial Balance.
 *
 * The figures come from the same server engine as the PDF / XLSX exports
 * (`dynamic.trial.balance.engine.get_report_data`). Option toggles re-run the engine,
 * the search box filters the loaded lines client-side (keeping their parent groups),
 * groups can be folded and account lines open their journal items.
 */
export class TrialBalancePreview extends Component {
    static template = "account_dynamic_trial_balance.TrialBalancePreview";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.sections = SECTIONS;
        this.state = useState({
            options: this.initialOptions(),
            data: null,
            search: "",
            folded: new Set(),
            loading: false,
        });
        onWillStart(() => this.load());
    }

    /**
     * Options come from the wizard (action params). When the page is reloaded the web client
     * restores the action from the URL without params: fall back to the last options used in
     * this browser tab, then to the current month.
     */
    initialOptions() {
        const fromWizard = this.props.action.params?.options;
        if (fromWizard?.date_from) {
            return { ...fromWizard };
        }
        try {
            const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null");
            if (saved?.date_from) {
                return saved;
            }
        } catch {
            // storage unavailable: use the defaults below
        }
        const today = luxon.DateTime.local();
        return {
            date_from: today.startOf("month").toISODate(),
            date_to: today.toISODate(),
        };
    }

    /** (Re)compute the report on the server with the current options. */
    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("dynamic.trial.balance.engine", "get_report_data", [
                this.state.options,
            ]);
            this.state.options = this.state.data.options;
            try {
                sessionStorage.setItem(STORAGE_KEY, JSON.stringify(this.state.options));
            } catch {
                // storage unavailable: reload falls back to the current month
            }
        } finally {
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------
    // Getters
    // ------------------------------------------------------------------

    get showCurrency() {
        return this.state.data?.options.show_amount_currency;
    }

    /**
     * Lines to render: the search term keeps matching lines and their parent groups,
     * then the lines located under a folded group are hidden.
     */
    get visibleLines() {
        const data = this.state.data;
        if (!data) {
            return [];
        }
        const byId = Object.fromEntries(data.lines.map((line) => [line.id, line]));
        const term = this.state.search.trim().toLowerCase();

        let keep = null;
        if (term) {
            keep = new Set();
            for (const line of data.lines) {
                if (`${line.code} ${line.name}`.toLowerCase().includes(term)) {
                    // keep the matching line and all its parent groups
                    let current = line;
                    while (current) {
                        keep.add(current.id);
                        current = current.parent_id && byId[current.parent_id];
                    }
                }
            }
        }

        return data.lines.filter((line) => {
            if (keep && !keep.has(line.id)) {
                return false;
            }
            // hide lines below a folded group
            let parentId = line.parent_id;
            while (parentId) {
                if (this.state.folded.has(parentId)) {
                    return false;
                }
                parentId = byId[parentId]?.parent_id;
            }
            return true;
        });
    }

    get filterBadges() {
        return this.state.data?.header.filters || [];
    }

    // ------------------------------------------------------------------
    // Formatting
    // ------------------------------------------------------------------

    /** Amount in company currency; zero amounts are left blank to keep the table readable. */
    formatAmount(value) {
        if (!value) {
            return "";
        }
        return formatMonetary(value, { currencyId: this.state.data.company_currency.id });
    }

    formatAmountCurrency(line) {
        if (!line.currency) {
            return "";
        }
        return formatMonetary(line.amount_currency, { currencyId: line.currency.id });
    }

    lineClass(line) {
        return {
            "o_dtb_group fw-bold": line.type === "group",
            "o_dtb_account": line.type === "account",
            "o_dtb_total fw-bold": line.type === "total",
        };
    }

    /** Indentation of the code cell according to the hierarchy level. */
    indent(line) {
        return `padding-left: ${0.5 + Math.max(line.level - 1, 0) * 1.25}rem;`;
    }

    // ------------------------------------------------------------------
    // Handlers
    // ------------------------------------------------------------------

    /** Flip a boolean option and recompute (disabling the hierarchy also disables "only parents"). */
    async toggleOption(name) {
        this.state.options = { ...this.state.options, [name]: !this.state.options[name] };
        if (name === "hierarchy" && !this.state.options.hierarchy) {
            this.state.options.only_parents = false;
        }
        this.state.folded = new Set();
        await this.load();
    }

    async setLevel(ev) {
        this.state.options = { ...this.state.options, account_level: parseInt(ev.target.value) };
        await this.load();
    }

    async setDate(name, ev) {
        if (!ev.target.value) {
            return;
        }
        this.state.options = { ...this.state.options, [name]: ev.target.value };
        await this.load();
    }

    onSearch(ev) {
        this.state.search = ev.target.value;
    }

    /** Fold / unfold a group line (client-side only, no server call). */
    toggleFold(line) {
        if (line.type !== "group" || this.state.options.only_parents) {
            return;
        }
        const folded = new Set(this.state.folded);
        folded.has(line.id) ? folded.delete(line.id) : folded.add(line.id);
        this.state.folded = folded;
    }

    /**
     * Drill-down: open the journal items behind an account line, with the same state,
     * journal, analytic and currency filters as the report (all dates up to the end date).
     */
    openJournalItems(line) {
        if (line.type !== "account") {
            return;
        }
        const options = this.state.data.options;
        const domain = [
            ["account_id", "=", line.account_id],
            ["date", "<=", options.date_to],
            ["parent_state", "in", options.include_unposted ? ["posted", "draft"] : ["posted"]],
        ];
        if (line.currency) {
            domain.push(["currency_id", "=", line.currency.id]);
        }
        if (options.journal_ids.length) {
            domain.push(["journal_id", "in", options.journal_ids]);
        }
        if (options.analytic_account_ids.length) {
            domain.push(["analytic_distribution", "in", options.analytic_account_ids]);
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `${line.code} ${line.name}`,
            res_model: "account.move.line",
            views: [[false, "list"], [false, "form"]],
            domain,
            context: { search_default_group_by_move: 0 },
        });
    }

    /**
     * Export what is on screen: a wizard is created from the current options and its
     * `action_pdf` / `action_xlsx` button method is executed.
     */
    async export(method) {
        const wizardId = await this.orm.call("dynamic.trial.balance.wizard", "create_from_options", [
            this.state.data.options,
        ]);
        const action = await this.orm.call("dynamic.trial.balance.wizard", method, [[wizardId]]);
        await this.actionService.doAction(action);
    }
}

registry.category("actions").add("account_dynamic_trial_balance.preview", TrialBalancePreview);
