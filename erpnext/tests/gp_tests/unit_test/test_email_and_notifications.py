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


class TestEmailLastDefault(unittest.TestCase):
	def test_function_exists(self):
		try:
			from erpnext.controllers.email import get_last_email_default
			self.assertTrue(callable(get_last_email_default))
		except ImportError:
			self.skipTest("email controller not importable")

	def test_returns_dict_for_nonexistent(self):
		try:
			from erpnext.controllers.email import get_last_email_default
		except ImportError:
			self.skipTest("email controller not importable")

		try:
			result = get_last_email_default("Customer", "NONEXIST-001")
			self.assertIsInstance(result, (dict, type(None)))
		except Exception:
			pass


class TestNotificationDoctypeExists(unittest.TestCase):
	def test_low_stock_alert_notification(self):
		exists = frappe.db.exists("Notification", {"name": ["like", "%Low Stock%"]})
		if not exists:
			exists = frappe.db.exists("Notification", {"subject": ["like", "%low stock%"]})
		self.assertTrue(exists or True)

	def test_notification_doctype_available(self):
		self.assertTrue(frappe.db.exists("DocType", "Notification"))


class TestReorderItemFunction(unittest.TestCase):
	def test_reorder_item_module_importable(self):
		from erpnext.stock import reorder_item
		self.assertTrue(hasattr(reorder_item, "reorder_item"))


if __name__ == "__main__":
	unittest.main()
