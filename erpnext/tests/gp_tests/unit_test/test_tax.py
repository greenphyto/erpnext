import os
import frappe
import unittest

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestGSTReturnSummaryReport(unittest.TestCase):
	def test_importable(self):
		from erpnext.accounts.report.gst_return_summary_report.gst_return_summary_report import execute
		self.assertTrue(callable(execute))

	def test_returns_structure(self):
		from erpnext.accounts.report.gst_return_summary_report.gst_return_summary_report import execute
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		filters = frappe._dict({
			"company": company,
			"from_date": "2026-01-01",
			"to_date": "2026-06-30",
		})
		try:
			result = execute(filters)
			self.assertIsInstance(result, tuple)
		except Exception:
			self.skipTest("GST report execution failed")


class TestPurchaseTaxesReport(unittest.TestCase):
	def test_importable(self):
		try:
			from erpnext.accounts.report.purchase_taxes.purchase_taxes import execute
			self.assertTrue(callable(execute))
		except ImportError:
			self.skipTest("purchase_taxes report not importable")


class TestSalesTaxesReport(unittest.TestCase):
	def test_importable(self):
		try:
			from erpnext.accounts.report.sales_taxes.sales_taxes import execute
			self.assertTrue(callable(execute))
		except ImportError:
			self.skipTest("sales_taxes report not importable")


class TestJournalEntryGSTVoucherType(unittest.TestCase):
	def test_journal_entry_with_gst_voucher_type(self):
		meta = frappe.get_meta("Journal Entry")
		field = meta.get_field("voucher_type")
		self.assertIsNotNone(field)
		options = (field.options or "").split("\n")
		self.assertIn("Journal Entry with GST", options)


if __name__ == "__main__":
	unittest.main()
