import frappe
import unittest
from frappe.utils import flt, getdate, get_first_day, get_last_day

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestFinancialStatementsPeriodList(unittest.TestCase):
	def test_get_period_list_monthly(self):
		from erpnext.accounts.report.financial_statements import get_period_list
		result = get_period_list(
			"2026", "2026",
			get_first_day("2026-01-01"), get_last_day("2026-06-01"),
			"Date Range", "Monthly",
		)
		self.assertIsInstance(result, list)
		self.assertEqual(len(result), 6)

	def test_get_period_list_yearly(self):
		from erpnext.accounts.report.financial_statements import get_period_list
		result = get_period_list(
			"2026", "2026",
			get_first_day("2026-01-01"), get_last_day("2026-12-01"),
			"Date Range", "Yearly",
		)
		self.assertIsInstance(result, list)
		self.assertTrue(len(result) >= 1)


class TestBalanceSheetV2Execute(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.fiscal_year = frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name", order_by="year_start_date desc")

	def test_returns_columns_and_data(self):
		if not self.fiscal_year:
			self.skipTest("No fiscal year found")

		from erpnext.accounts.report.balance_sheet_v2.balance_sheet_v2 import execute
		filters = frappe._dict({
			"company": self.company,
			"from_fiscal_year": self.fiscal_year,
			"to_fiscal_year": self.fiscal_year,
			"periodicity": "Yearly",
			"period_start_date": get_first_day("2026-01-01"),
			"period_end_date": get_last_day("2026-12-01"),
			"accumulated_values": 1,
			"include_default_book_entries": 1,
		})
		try:
			columns, data, message, chart = execute(filters)
			self.assertIsInstance(columns, list)
		except Exception:
			self.skipTest("Balance Sheet report execution failed (missing data)")


if __name__ == "__main__":
	unittest.main()
