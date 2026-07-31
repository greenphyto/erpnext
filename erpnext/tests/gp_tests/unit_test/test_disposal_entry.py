import os
import frappe
import unittest
from frappe.utils import cint, flt, nowdate, getdate, add_days

from erpnext.assets.doctype.asset.depreciation import (
	check_future_posted_depreciation,
	_warn_unposted_depreciation,
	check_unposted_depr_before_disposal,
	scrap_asset,
)

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestCheckFuturePostedDepreciation(unittest.TestCase):
	def test_no_schedules_returns_empty(self):
		asset = frappe.new_doc("Asset")
		asset.schedules = []
		result = check_future_posted_depreciation(asset, nowdate())
		self.assertEqual(result, [])

	def test_posted_entry_after_disposal_date_is_returned(self):
		asset = frappe.new_doc("Asset")
		asset.append("schedules", {
			"schedule_date": "2026-12-31",
			"journal_entry": "JE-FUTURE-001",
			"depreciation_amount": 1000,
			"finance_book_id": 1,
		})
		asset.append("schedules", {
			"schedule_date": "2026-01-31",
			"journal_entry": "JE-PAST-001",
			"depreciation_amount": 1000,
			"finance_book_id": 1,
		})
		result = check_future_posted_depreciation(asset, "2026-06-30")
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["journal_entry"], "JE-FUTURE-001")

	def test_posted_entry_before_disposal_date_not_returned(self):
		asset = frappe.new_doc("Asset")
		asset.append("schedules", {
			"schedule_date": "2026-01-31",
			"journal_entry": "JE-PAST-001",
			"depreciation_amount": 1000,
			"finance_book_id": 1,
		})
		result = check_future_posted_depreciation(asset, "2026-06-30")
		self.assertEqual(result, [])

	def test_unposted_entry_after_disposal_not_returned(self):
		asset = frappe.new_doc("Asset")
		asset.append("schedules", {
			"schedule_date": "2026-12-31",
			"journal_entry": None,
			"depreciation_amount": 1000,
			"finance_book_id": 1,
		})
		result = check_future_posted_depreciation(asset, "2026-06-30")
		self.assertEqual(result, [])


class TestScrapAssetValidation(unittest.TestCase):
	def test_draft_asset_throws(self):
		asset_name = frappe.db.get_value("Asset", {"docstatus": 0}, "name")
		if not asset_name:
			self.skipTest("No draft asset found in test5")
		self.assertRaises(Exception, scrap_asset, asset_name)

	def test_already_scrapped_asset_throws(self):
		asset_name = frappe.db.get_value("Asset", {"status": "Scrapped", "docstatus": 1}, "name")
		if not asset_name:
			self.skipTest("No scrapped asset found in test5")
		self.assertRaises(Exception, scrap_asset, asset_name)


class TestCheckUnpostedDeprBeforeDisposal(unittest.TestCase):
	def test_returns_dict_structure(self):
		asset_name = frappe.db.get_value("Asset", {"docstatus": 1, "status": ["not in", ["Scrapped", "Sold"]]}, "name")
		if not asset_name:
			self.skipTest("No submitted asset found in test5")

		result = check_unposted_depr_before_disposal(asset_name, nowdate())
		self.assertIsInstance(result, dict)
		self.assertIn("unposted_count", result)
		self.assertIn("disposal_date", result)
		self.assertIn("future_posted", result)

	def test_defaults_disposal_date_to_today(self):
		asset_name = frappe.db.get_value("Asset", {"docstatus": 1, "status": ["not in", ["Scrapped", "Sold"]]}, "name")
		if not asset_name:
			self.skipTest("No submitted asset found in test5")

		result = check_unposted_depr_before_disposal(asset_name)
		self.assertEqual(str(result["disposal_date"]), nowdate())


if __name__ == "__main__":
	unittest.main()
