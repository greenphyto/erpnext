import frappe
import unittest
from frappe.utils import flt, getdate, nowdate, get_last_day, add_months

from erpnext.assets.doctype.asset.depreciation import (
	get_month_year,
	get_depreciable_assets,
	check_future_posted_depreciation,
)

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestGetMonthYear(unittest.TestCase):
	def test_format_january(self):
		self.assertEqual(get_month_year("2026-01-15"), "01 2026")

	def test_format_december(self):
		self.assertEqual(get_month_year("2026-12-31"), "12 2026")

	def test_format_single_digit_month(self):
		self.assertEqual(get_month_year("2026-03-01"), "03 2026")


class TestGetDepreciableAssets(unittest.TestCase):
	def test_returns_list(self):
		date = get_last_day(add_months(nowdate(), -1))
		result = get_depreciable_assets(date)
		self.assertIsInstance(result, list)

	def test_with_asset_category_filter(self):
		category = frappe.db.get_value("Asset Category", {}, "name")
		if not category:
			self.skipTest("No asset category found")
		date = get_last_day(add_months(nowdate(), -1))
		result = get_depreciable_assets(date, asset_category=[category])
		self.assertIsInstance(result, list)


class TestCheckFuturePostedDepreciation(unittest.TestCase):
	def test_no_schedules_returns_empty(self):
		asset = frappe.new_doc("Asset")
		asset.schedules = []
		result = check_future_posted_depreciation(asset, nowdate())
		self.assertEqual(result, [])

	def test_future_posted_detected(self):
		asset = frappe.new_doc("Asset")
		asset.append("schedules", {
			"schedule_date": "2099-12-31",
			"journal_entry": "JE-TEST-001",
			"depreciation_amount": 500,
			"finance_book_id": 1,
		})
		result = check_future_posted_depreciation(asset, nowdate())
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["journal_entry"], "JE-TEST-001")

	def test_past_posted_not_detected(self):
		asset = frappe.new_doc("Asset")
		asset.append("schedules", {
			"schedule_date": "2020-01-31",
			"journal_entry": "JE-OLD-001",
			"depreciation_amount": 500,
			"finance_book_id": 1,
		})
		result = check_future_posted_depreciation(asset, nowdate())
		self.assertEqual(result, [])


if __name__ == "__main__":
	unittest.main()
