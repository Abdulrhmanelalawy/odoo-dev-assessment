"""HTTP endpoint serving the XLSX export of the Dynamic Trial Balance."""

from odoo import fields, http
from odoo.http import content_disposition, request


class TrialBalanceController(http.Controller):

    @http.route("/account_dynamic_trial_balance/xlsx/<int:wizard_id>", type="http", auth="user", methods=["GET"])
    def download_xlsx(self, wizard_id):
        """Stream the XLSX file of a wizard as an attachment download.

        Transient records are only readable by their creator (implicit record rule of
        ``TransientModel``), so a user cannot download another user's report.
        """
        wizard = request.env["dynamic.trial.balance.wizard"].browse(wizard_id).exists()
        if not wizard:
            raise request.not_found()
        wizard.check_access("read")
        content = wizard._generate_xlsx()
        filename = "Trial Balance %s - %s.xlsx" % (
            fields.Date.to_string(wizard.date_from), fields.Date.to_string(wizard.date_to)
        )
        return request.make_response(content, headers=[
            ("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("Content-Disposition", content_disposition(filename)),
        ])
