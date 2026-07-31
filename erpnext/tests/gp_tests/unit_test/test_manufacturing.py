import frappe
import unittest
from frappe.utils import flt, cint, cstr

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestWorkOrderCalculateOperatingCost(unittest.TestCase):
	def test_per_hour_calculation(self):
		wo = frappe.new_doc("Work Order")
		wo.gross_weight = 10
		wo.additional_operating_cost = 0
		wo.corrective_operation_cost = 0
		wo.append("operations", {
			"operation": "Test Op",
			"calculation_type": "Per Hour",
			"operation_rate": 60,
			"time_in_mins": 120,
			"actual_operation_time": 90,
		})
		wo.calculate_operating_cost()
		self.assertAlmostEqual(wo.operations[0].planned_operating_cost, 120.0, places=2)
		self.assertAlmostEqual(wo.operations[0].actual_operating_cost, 90.0, places=2)

	def test_per_kg_calculation(self):
		wo = frappe.new_doc("Work Order")
		wo.gross_weight = 50
		wo.additional_operating_cost = 0
		wo.corrective_operation_cost = 0
		wo.append("operations", {
			"operation": "Test Op",
			"calculation_type": "Per KG",
			"operation_rate": 2,
			"time_in_mins": 60,
			"actual_operation_time": 60,
		})
		wo.calculate_operating_cost()
		self.assertAlmostEqual(wo.operations[0].planned_operating_cost, 100.0, places=2)
		self.assertAlmostEqual(wo.operations[0].actual_operating_cost, 100.0, places=2)

	def test_total_operating_cost_includes_additional(self):
		wo = frappe.new_doc("Work Order")
		wo.gross_weight = 10
		wo.additional_operating_cost = 50
		wo.corrective_operation_cost = 20
		wo.append("operations", {
			"operation": "Test",
			"calculation_type": "Per KG",
			"operation_rate": 5,
			"time_in_mins": 0,
			"actual_operation_time": 0,
		})
		wo.calculate_operating_cost()
		expected_total = 50 + 20 + 50
		self.assertAlmostEqual(wo.total_operating_cost, expected_total, places=2)


class TestWorkOrderGetStatus(unittest.TestCase):
	def test_draft_status(self):
		wo = frappe.new_doc("Work Order")
		wo.docstatus = 0
		wo.status = ""
		result = wo.get_status()
		self.assertEqual(result, "Draft")

	def test_cancelled_status(self):
		wo = frappe.new_doc("Work Order")
		wo.docstatus = 2
		wo.status = ""
		result = wo.get_status()
		self.assertEqual(result, "Cancelled")


class TestItemMaterialGroupMapping(unittest.TestCase):
	def test_rm_sd_maps_to_seeds(self):
		item = frappe.new_doc("Item")
		item.item_code = "RM-SD-001"
		result = item.get_item_material_group()
		self.assertEqual(result, "Seeds")

	def test_pr_lv_maps_to_lettuce(self):
		item = frappe.new_doc("Item")
		item.item_code = "PR-LV-001"
		result = item.get_item_material_group()
		self.assertEqual(result, "Vegetables (Lettuce)")

	def test_pr_av_maps_to_asian_vegetables(self):
		item = frappe.new_doc("Item")
		item.item_code = "PR-AV-001"
		result = item.get_item_material_group()
		self.assertEqual(result, "Vegetables (Asian Vegetables)")

	def test_zot_maps_to_other_packaging(self):
		item = frappe.new_doc("Item")
		item.item_code = "ZOT-001"
		result = item.get_item_material_group()
		self.assertEqual(result, "Other Packaging")

	def test_unknown_prefix_returns_empty(self):
		item = frappe.new_doc("Item")
		item.item_code = "UNKNOWN-001"
		result = item.get_item_material_group()
		self.assertEqual(result, "")

	def test_set_data_flag(self):
		item = frappe.new_doc("Item")
		item.item_code = "RM-NS-001"
		item.material_group = ""
		item.get_item_material_group(set_data=True)
		self.assertEqual(item.material_group, "Nutrition")


class TestChangeNamingSeries(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.abbr = frappe.get_value("Company", self.company, "series_abbr")

	def test_prepends_company_abbr(self):
		if not self.abbr:
			self.skipTest("No series_abbr for company")

		from erpnext.controllers.erp import change_naming_series

		doc = frappe.new_doc("Sales Invoice")
		doc.company = self.company
		doc.naming_series = "SI-.YYYY.-.####"
		change_naming_series(doc)
		self.assertTrue(doc.naming_series.startswith(self.abbr))

	def test_does_not_double_prepend(self):
		if not self.abbr:
			self.skipTest("No series_abbr for company")

		from erpnext.controllers.erp import change_naming_series

		doc = frappe.new_doc("Sales Invoice")
		doc.company = self.company
		doc.naming_series = f"{self.abbr}SI-.YYYY.-.####"
		change_naming_series(doc)
		self.assertFalse(doc.naming_series.startswith(self.abbr + self.abbr))

	def test_non_listed_doctype_skipped(self):
		from erpnext.controllers.erp import change_naming_series

		doc = frappe.new_doc("Customer")
		doc.company = self.company if hasattr(doc, 'company') else ""
		original = doc.get("naming_series") or ""
		change_naming_series(doc)
		self.assertEqual(doc.get("naming_series") or "", original)


if __name__ == "__main__":
	unittest.main()
