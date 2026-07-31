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


class TestRepostItemValuation(unittest.TestCase):
	def test_doctype_exists(self):
		self.assertTrue(frappe.db.exists("DocType", "Repost Item Valuation"))

	def test_has_error_log_field(self):
		meta = frappe.get_meta("Repost Item Valuation")
		self.assertTrue(meta.has_field("error_log"))

	def test_repost_function_importable(self):
		from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import repost
		self.assertTrue(callable(repost))


class TestStockRepostingSettings(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "Stock Reposting Settings")
		if not exists:
			self.skipTest("Stock Reposting Settings not found")
		self.assertTrue(exists)

	def test_has_timeslot_field(self):
		if not frappe.db.exists("DocType", "Stock Reposting Settings"):
			self.skipTest("Stock Reposting Settings not found")
		meta = frappe.get_meta("Stock Reposting Settings")
		self.assertTrue(meta.has_field("limit_reposting_timeslot"))


class TestInConfiguredTimeslot(unittest.TestCase):
	def test_function_importable(self):
		from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import in_configured_timeslot
		self.assertTrue(callable(in_configured_timeslot))

	def test_returns_boolean(self):
		from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import in_configured_timeslot
		result = in_configured_timeslot()
		self.assertIsInstance(result, bool)


if __name__ == "__main__":
	unittest.main()
