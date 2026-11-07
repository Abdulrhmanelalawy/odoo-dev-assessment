"""Tests of the salesperson / receipt layout integration module."""

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestSalespersonOnCustomReceipt(TestPointOfSaleHttpCommon):

    def test_module_is_auto_installed(self):
        module = self.env["ir.module.module"].search([("name", "=", "pos_salesperson_receipt_layout")])
        self.assertTrue(module.auto_install)

    def test_salesperson_on_receipt_layout_tour(self):
        salesperson = self.env["pos.sale.person"].create({"name": "Salesperson A"})
        self.main_pos_config.write({
            "active_salesperson_feature": True,
            "allowed_sale_person_ids": [Command.set(salesperson.ids)],
            "use_customized_receipt": True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("PosSalespersonOnReceiptLayoutTour", login="pos_user")
        line = self.main_pos_config.current_session_id.order_ids.lines
        self.assertEqual(line.salesperson_id, salesperson)
