"""Tests of the receipt layout: HTML sanitization, session payload and printed receipts (tours)."""

import base64

from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestPosReceiptLayout(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with file_open("base/static/img/res_company_logo.png", "rb") as logo:
            cls.logo = base64.b64encode(logo.read())

    def _enable_receipt_layout(self, **values):
        self.main_pos_config.write({
            "use_customized_receipt": True,
            "receipt_logo": self.logo,
            "company_name": "<p><b>My Custom Shop</b><script>alert('x')</script></p>",
            "company_details": "<p>Street 1, Cairo<br/>VAT 123</p>",
            "show_customer_details": True,
            **values,
        })

    def test_html_fields_are_sanitized(self):
        self._enable_receipt_layout()
        self.assertIn("<b>My Custom Shop</b>", self.main_pos_config.company_name)
        self.assertNotIn("<script", self.main_pos_config.company_name)

    def test_logo_not_shipped_in_session_payload(self):
        self._enable_receipt_layout()
        data = self.env["pos.config"]._load_pos_data_read(self.main_pos_config, self.main_pos_config)[0]
        self.assertNotIn("receipt_logo", data)
        self.assertTrue(data["_has_receipt_logo"])
        self.assertTrue(data["use_customized_receipt"])

    def test_receipt_layout_tour(self):
        self._enable_receipt_layout()
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("PosReceiptLayoutTour", login="pos_user")

    def test_receipt_layout_without_customer_tour(self):
        self._enable_receipt_layout(show_customer_details=False)
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("PosReceiptLayoutNoCustomerTour", login="pos_user")

    def test_default_receipt_tour(self):
        # Fields filled but feature off: everything must be ignored (backward compatibility)
        self._enable_receipt_layout(use_customized_receipt=False)
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("PosDefaultReceiptTour", login="pos_user")
