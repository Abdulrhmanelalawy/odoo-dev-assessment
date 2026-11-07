"""Tests of the salesperson assignment: POS data loading (offline availability) and browser tours."""

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestPosSalesperson(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        SalePerson = cls.env["pos.sale.person"]
        cls.sp_a = SalePerson.create({"name": "Salesperson A", "phone_number": "0100"})
        cls.sp_b = SalePerson.create({"name": "Salesperson B"})
        cls.sp_c = SalePerson.create({"name": "Salesperson C"})
        cls.sp_other = SalePerson.create({"name": "Not Allowed Here"})

    def _loaded_salespersons(self, config):
        return self.env["pos.sale.person"]._load_pos_data_search_read({}, config)

    # ------------------------------------------------------------------
    # Data loading (what reaches the POS, hence what is available offline)
    # ------------------------------------------------------------------

    def test_nothing_loaded_when_feature_disabled(self):
        self.main_pos_config.write({
            "active_salesperson_feature": False,
            "allowed_sale_person_ids": [Command.set(self.sp_a.ids)],
        })
        self.assertEqual(self._loaded_salespersons(self.main_pos_config), [])

    def test_only_allowed_salespersons_loaded(self):
        self.main_pos_config.write({
            "active_salesperson_feature": True,
            "allowed_sale_person_ids": [Command.set((self.sp_a | self.sp_b).ids)],
        })
        loaded = self._loaded_salespersons(self.main_pos_config)
        self.assertEqual({r["name"] for r in loaded}, {"Salesperson A", "Salesperson B"})
        self.assertEqual(set(loaded[0]), {"id", "name", "phone_number"})

    def test_all_active_salespersons_when_no_restriction(self):
        self.sp_other.active = False
        self.main_pos_config.write({"active_salesperson_feature": True, "allowed_sale_person_ids": [Command.clear()]})
        names = {r["name"] for r in self._loaded_salespersons(self.main_pos_config)}
        self.assertEqual(names, {"Salesperson A", "Salesperson B", "Salesperson C"})

    def test_order_line_field_is_synced(self):
        fields = self.env["pos.order.line"]._load_pos_data_fields(self.main_pos_config)
        self.assertIn("salesperson_id", fields)
        self.assertIn("pos.sale.person", self.env["pos.session"]._load_pos_data_models(self.main_pos_config))

    # ------------------------------------------------------------------
    # End-to-end (browser tours driving the POS UI)
    # ------------------------------------------------------------------

    def test_salesperson_tour(self):
        self.main_pos_config.write({
            "active_salesperson_feature": True,
            "allowed_sale_person_ids": [Command.set((self.sp_a | self.sp_b | self.sp_c).ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("PosSalespersonAssignmentTour", login="pos_user")

        orders = self.main_pos_config.current_session_id.order_ids.sorted("id")
        self.assertEqual(len(orders), 3, "the offline order must have been synced as well")
        individual, overwritten, unassigned = orders

        # per-line assignment (made offline), no merge into a credited line
        lines = individual.lines.sorted("id")
        self.assertEqual(
            [(l.product_id.name, l.salesperson_id.name or False) for l in lines],
            [("Desk Organizer", "Salesperson A"), ("Letter Tray", "Salesperson B"), ("Desk Organizer", False)],
        )
        # the order-level assignment overwrote the per-line ones
        self.assertEqual(set(overwritten.lines.salesperson_id.mapped("name")), {"Salesperson C"})
        self.assertEqual(len(overwritten.lines), 2)
        # nothing assigned
        self.assertFalse(unassigned.lines.salesperson_id)

    def test_salesperson_ui_hidden_when_disabled(self):
        self.main_pos_config.write({
            "active_salesperson_feature": False,
            "allowed_sale_person_ids": [Command.set(self.sp_a.ids)],  # must be ignored
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("PosSalespersonDisabledTour", login="pos_user")
