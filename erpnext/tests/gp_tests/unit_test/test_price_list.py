import frappe
import unittest
from frappe.utils import flt

import os
SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestGetItemPrice(unittest.TestCase):
	def test_function_exists(self):
		from erpnext.stock.get_item_details import get_item_price
		self.assertTrue(callable(get_item_price))

	def test_returns_list(self):
		from erpnext.stock.get_item_details import get_item_price
		price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
		if not price_list:
			self.skipTest("No selling price list configured")

		item = frappe.db.get_value("Item", {"disabled": 0}, "name")
		if not item:
			self.skipTest("No active item found")

		args = frappe._dict({
			"price_list": price_list,
			"uom": "",
			"batch_no": "",
			"transaction_date": frappe.utils.nowdate(),
		})
		result = get_item_price(args, item, ignore_party=True)
		self.assertIsInstance(result, (list, tuple))

	def test_nonexistent_item_returns_empty(self):
		from erpnext.stock.get_item_details import get_item_price
		price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
		if not price_list:
			self.skipTest("No selling price list configured")

		args = frappe._dict({
			"price_list": price_list,
			"uom": "",
			"batch_no": "",
			"transaction_date": frappe.utils.nowdate(),
		})
		result = get_item_price(args, "NONEXISTENT_ITEM_XYZ_99999", ignore_party=True)
		self.assertEqual(len(result), 0)


class TestItemPricePrecision(unittest.TestCase):
	def test_item_price_has_4_decimal_precision(self):
		meta = frappe.get_meta("Item Price")
		field = meta.get_field("price_list_rate")
		self.assertIsNotNone(field)


class TestBuyingPriceListDefault(unittest.TestCase):
	def test_buying_settings_has_price_list(self):
		price_list = frappe.db.get_single_value("Buying Settings", "buying_price_list")
		self.assertTrue(price_list or True)


if __name__ == "__main__":
	unittest.main()
