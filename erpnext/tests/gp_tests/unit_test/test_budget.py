import os
import frappe
import unittest
from frappe.utils import flt, getdate, get_first_day, get_last_day

from erpnext.gp_erp.report.budget_variance_greenphyto.budget_variance_greenphyto import (
	control_filters,
	get_budget_account,
	get_budget_data,
	add_summary_columns,
)

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestControlFilters(unittest.TestCase):
	def test_sets_fiscal_year(self):
		filters = frappe._dict({
			"year": "2026",
			"month": "01",
			"to_month": "06",
		})
		result = control_filters(filters)
		self.assertEqual(result.from_fiscal_year, "2026")
		self.assertEqual(result.to_fiscal_year, "2026")

	def test_sets_period_dates(self):
		filters = frappe._dict({
			"year": "2026",
			"month": "03",
			"to_month": "05",
		})
		result = control_filters(filters)
		self.assertEqual(result.period_start_date, get_first_day("2026-03-01"))
		self.assertEqual(result.period_end_date, get_last_day("2026-05-01"))

	def test_single_month_range(self):
		filters = frappe._dict({
			"year": "2026",
			"month": "07",
			"to_month": "07",
		})
		result = control_filters(filters)
		self.assertEqual(result.period_start_date, get_first_day("2026-07-01"))
		self.assertEqual(result.period_end_date, get_last_day("2026-07-01"))


class TestGetBudgetAccount(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_returns_list(self):
		result = get_budget_account(company=self.company)
		self.assertIsInstance(result, list)

	def test_with_cost_center_filter(self):
		cost_center = frappe.db.get_value("Cost Center", {"company": self.company, "is_group": 0}, "name")
		if not cost_center:
			self.skipTest("No cost center found")
		result = get_budget_account(cost_center=[cost_center], company=self.company)
		self.assertIsInstance(result, list)


class TestGetBudgetData(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.fiscal_year = frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name", order_by="year_start_date desc")

	def test_returns_dict(self):
		if not self.fiscal_year:
			self.skipTest("No fiscal year found")

		filters = frappe._dict({
			"company": self.company,
			"from_fiscal_year": self.fiscal_year,
			"to_fiscal_year": self.fiscal_year,
			"budget_against": "Cost Center",
			"periodicity": "Monthly",
			"cost_center": [],
		})
		result = get_budget_data(filters)
		self.assertIsInstance(result, dict)


class TestAddSummaryColumns(unittest.TestCase):
	def test_calculates_totals(self):
		period_list = [
			frappe._dict({"key": "jan_2026"}),
			frappe._dict({"key": "feb_2026"}),
			frappe._dict({"key": "mar_2026"}),
		]
		rows = [
			{
				"account": "Test Account",
				"jan_2026": 100,
				"feb_2026": 200,
				"mar_2026": 300,
				"jan_2026_budget": 150,
				"feb_2026_budget": 250,
				"mar_2026_budget": 350,
			}
		]
		add_summary_columns(rows, period_list)
		self.assertEqual(rows[0]["total_actual"], 600)
		self.assertEqual(rows[0]["budget_ytd"], 750)
		self.assertEqual(rows[0]["variance_amount"], -150)
		self.assertAlmostEqual(rows[0]["variance_percent"], -20.0, places=1)

	def test_zero_budget_variance_percent_is_zero(self):
		period_list = [frappe._dict({"key": "jan_2026"})]
		rows = [
			{
				"account": "Test",
				"jan_2026": 100,
				"jan_2026_budget": 0,
			}
		]
		add_summary_columns(rows, period_list)
		self.assertEqual(rows[0]["variance_percent"], 0)

	def test_skips_profit_data_row(self):
		period_list = [frappe._dict({"key": "jan_2026"})]
		rows = [
			{
				"account": "Net Profit",
				"profit_data": True,
				"jan_2026": 500,
				"jan_2026_budget": 400,
			}
		]
		add_summary_columns(rows, period_list)
		self.assertNotIn("total_actual", rows[0])


if __name__ == "__main__":
	unittest.main()
