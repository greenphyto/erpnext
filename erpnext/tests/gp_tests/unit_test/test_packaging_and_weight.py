import frappe
import unittest
from frappe.utils import flt, cint
import math

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestCalculateNetTotalPkg(unittest.TestCase):
	def test_basic_calculation(self):
		ps = frappe.new_doc("Packing Slip")
		ps.unit_per_carton = 12
		ps.carton_weight = 0.435
		ps.flags.first_fetch = True
		ps.append("items", {
			"item_code": "TEST",
			"qty": 24,
			"unit_weight": 0.2,
			"weight_uom": "Kg",
		})
		ps.calculate_net_total_pkg()

		item = ps.items[0]
		expected_cartons = math.ceil(24 / 12)
		expected_net = 0.2 * 24
		expected_gross = expected_net + (expected_cartons * 0.435)

		self.assertEqual(item.cartons, expected_cartons)
		self.assertAlmostEqual(item.net_weight, expected_net, places=4)
		self.assertAlmostEqual(item.gross_weight, expected_gross, places=4)
		self.assertEqual(item.uom_view, "200 Gr")

	def test_default_unit_per_carton(self):
		ps = frappe.new_doc("Packing Slip")
		ps.unit_per_carton = 0
		ps.carton_weight = 0
		ps.flags.first_fetch = True
		ps.append("items", {
			"item_code": "TEST",
			"qty": 5,
			"unit_weight": 0.15,
			"weight_uom": "Kg",
		})
		ps.calculate_net_total_pkg()
		self.assertEqual(ps.unit_per_carton, 12)
		self.assertEqual(ps.carton_weight, 0.435)

	def test_totals(self):
		ps = frappe.new_doc("Packing Slip")
		ps.unit_per_carton = 10
		ps.carton_weight = 0.5
		ps.flags.first_fetch = True
		ps.append("items", {
			"item_code": "A",
			"qty": 10,
			"unit_weight": 0.1,
			"weight_uom": "Kg",
		})
		ps.append("items", {
			"item_code": "B",
			"qty": 20,
			"unit_weight": 0.2,
			"weight_uom": "Kg",
		})
		ps.calculate_net_total_pkg()

		self.assertEqual(ps.total_qty, 30)
		net_a = 0.1 * 10
		net_b = 0.2 * 20
		self.assertAlmostEqual(ps.net_weight_pkg, round(net_a + net_b, 2), places=2)


if __name__ == "__main__":
	unittest.main()
