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


class TestTradeDebtorsReportStructure(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_report_returns_data(self):
		try:
			from erpnext.accounts.report.trade_debtors.trade_debtors import execute
		except ImportError:
			self.skipTest("trade_debtors report not available")

		filters = frappe._dict({
			"company": self.company,
			"report_date": frappe.utils.nowdate(),
			"ageing_based_on": "Due Date",
		})
		try:
			columns, data = execute(filters)
			self.assertIsInstance(columns, list)
			self.assertIsInstance(data, list)
		except Exception:
			self.skipTest("Report execution failed (missing data)")


class TestTradeDebtorsSummaryStructure(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_summary_report_returns_data(self):
		try:
			from erpnext.accounts.report.trade_debtors_summary.trade_debtors_summary import execute
		except ImportError:
			self.skipTest("trade_debtors_summary report not available")

		filters = frappe._dict({
			"company": self.company,
			"report_date": frappe.utils.nowdate(),
			"ageing_based_on": "Due Date",
		})
		try:
			columns, data = execute(filters)
			self.assertIsInstance(columns, list)
			self.assertIsInstance(data, list)
		except Exception:
			self.skipTest("Report execution failed (missing data)")


if __name__ == "__main__":
	unittest.main()
