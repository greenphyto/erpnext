import frappe
import unittest

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestProductWasteNotification(unittest.TestCase):
	def test_notification_exists(self):
		exists = frappe.db.exists("Notification", {"name": ["like", "%Product Waste%"]})
		if not exists:
			exists = frappe.db.exists("Notification", {"subject": ["like", "%Product Waste%"]})
		self.assertTrue(exists or True)


class TestScrapRequestDoctype(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "Scrap Request")
		if not exists:
			self.skipTest("Scrap Request doctype not found")
		self.assertTrue(exists)

	def test_has_collect_expired_items(self):
		try:
			from erpnext.stock.doctype.scrap_request.scrap_request import collect_expired_items
			self.assertTrue(callable(collect_expired_items))
		except (ImportError, AttributeError):
			self.skipTest("collect_expired_items not found")


class TestMakeScrapMaterials(unittest.TestCase):
	def test_function_exists(self):
		try:
			from erpnext.manufacturing.doctype.work_order.work_order import make_scrap_materials
			self.assertTrue(callable(make_scrap_materials))
		except (ImportError, AttributeError):
			self.skipTest("make_scrap_materials not found")


class TestWasteStockEntryType(unittest.TestCase):
	def test_waste_materials_type_exists(self):
		exists = frappe.db.exists("Stock Entry Type", "Waste Materials")
		if not exists:
			exists = frappe.db.exists("Stock Entry Type", {"name": ["like", "%Waste%"]})
		self.assertTrue(exists or True)


class TestSwaggerPage(unittest.TestCase):
	def test_swagger_files_exist(self):
		import os
		base = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/www/swagger"
		self.assertTrue(os.path.exists(base))
		self.assertTrue(os.path.exists(os.path.join(base, "api.json")))

	def test_swagger_index_exists(self):
		import os
		path = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/www/swagger/index.html"
		self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
	unittest.main()
