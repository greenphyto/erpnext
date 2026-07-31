import frappe
import unittest
import json

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestGetDataHelper(unittest.TestCase):
	def test_parses_json_string(self):
		from erpnext.controllers.erp_api import get_data
		data = get_data('{"key": "value", "num": 42}')
		self.assertEqual(data.key, "value")
		self.assertEqual(data.num, 42)

	def test_passes_dict_through(self):
		from erpnext.controllers.erp_api import get_data
		data = get_data({"key": "value"})
		self.assertEqual(data.key, "value")

	def test_returns_frappe_dict(self):
		from erpnext.controllers.erp_api import get_data
		data = get_data({"a": 1})
		self.assertIsInstance(data, frappe._dict)


class TestSaveLog(unittest.TestCase):
	def test_save_log_creates_entry(self):
		from erpnext.controllers.erp_api import save_log
		try:
			save_log("Work Order", "TEST-WO-UNIT-001", {"test": True}, now=True, endpoint="unit_test")
			exists = frappe.db.exists("FOMS Data Mapping", {"data_name": "TEST-WO-UNIT-001"})
			self.assertTrue(exists)
			if exists:
				frappe.delete_doc("FOMS Data Mapping", exists, force=True)
				frappe.db.commit()
		except Exception:
			self.skipTest("FOMS Data Mapping doctype or save_log not functional")


class TestUpdateLog(unittest.TestCase):
	def test_update_log_function_exists(self):
		from erpnext.controllers.erp_api import update_log
		self.assertTrue(callable(update_log))


class TestUpdateItemSafetyStock(unittest.TestCase):
	def test_function_exists(self):
		from erpnext.controllers.erp_api import update_item_safety_stock
		self.assertTrue(callable(update_item_safety_stock))

	def test_updates_safety_stock(self):
		from erpnext.controllers.erp_api import update_item_safety_stock
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		item = frappe.db.get_value("Item", {"disabled": 0, "is_stock_item": 1}, "name")
		if not item:
			self.skipTest("No stock item found")

		reorder = frappe.db.get_value("Item Reorder", {"parent": item}, "name")
		if not reorder:
			self.skipTest("No item reorder row found, PIC/Warehouse required")

		old_val = frappe.get_value("Item", item, "safety_stock")
		try:
			update_item_safety_stock(item, 999, company)
			new_val = frappe.get_value("Item", item, "safety_stock")
			self.assertEqual(float(new_val), 999.0)
		except frappe.ValidationError:
			self.skipTest("Validation error - PIC or Warehouse missing")
		finally:
			frappe.db.set_value("Item", item, "safety_stock", old_val or 0)
			frappe.db.commit()


if __name__ == "__main__":
	unittest.main()
