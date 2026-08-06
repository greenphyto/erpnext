import os
import frappe
import unittest
from frappe.utils import flt

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestNamingSeriesItemMaterialGroup(unittest.TestCase):
	def test_rm_sd_seeds(self):
		item = frappe.new_doc("Item")
		item.item_code = "RM-SD-TEST"
		self.assertEqual(item.get_item_material_group(), "Seeds")

	def test_rm_ns_nutrition(self):
		item = frappe.new_doc("Item")
		item.item_code = "RM-NS-TEST"
		self.assertEqual(item.get_item_material_group(), "Nutrition")

	def test_pdled_led(self):
		item = frappe.new_doc("Item")
		item.item_code = "PDLED-TEST"
		self.assertEqual(item.get_item_material_group(), "LED")

	def test_zgw_gateway(self):
		item = frappe.new_doc("Item")
		item.item_code = "ZGW-TEST"
		self.assertEqual(item.get_item_material_group(), "Gateway")

	def test_dmc_dimmer(self):
		item = frappe.new_doc("Item")
		item.item_code = "DMC-TEST"
		self.assertEqual(item.get_item_material_group(), "Dimmer Controller")

	def test_poc_power_connector(self):
		item = frappe.new_doc("Item")
		item.item_code = "POC-TEST"
		self.assertEqual(item.get_item_material_group(), "Power Connector")

	def test_zms_fg_systems(self):
		item = frappe.new_doc("Item")
		item.item_code = "ZMS-TEST"
		self.assertEqual(item.get_item_material_group(), "FG - Systems")

	def test_pd_trays(self):
		item = frappe.new_doc("Item")
		item.item_code = "PD-TEST"
		self.assertEqual(item.get_item_material_group(), "Trays & Boards")

	def test_tom_tooling(self):
		item = frappe.new_doc("Item")
		item.item_code = "TOM-TEST"
		self.assertEqual(item.get_item_material_group(), "Tooling & Moulding")

	def test_acc_accessories(self):
		item = frappe.new_doc("Item")
		item.item_code = "ACC-TEST"
		self.assertEqual(item.get_item_material_group(), "Accessories")


if __name__ == "__main__":
	unittest.main()
