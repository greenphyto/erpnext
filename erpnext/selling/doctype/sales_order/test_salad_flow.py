import frappe
from frappe.utils import nowdate, add_days, getdate, flt, random_string
from frappe.tests.utils import FrappeTestCase

CUSTOMER = "CMM Marketing Management Pte Ltd"
SALAD_ITEM = "Mesclun with rocket"
BOM_NAME = "BOM-Mesclun with rocket-0001"
COMPANY = "Greenphyto Pte Ltd"
WAREHOUSE = "Finished Goods - GPL"
WIP_WAREHOUSE = "Work In Progress - GPL"
TAX_TEMPLATE = "Singapore GST 0% - GPL"


class TestSaladFlow(FrappeTestCase):

	def setUp(self):
		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

	def test_01_sales_order_creates_bom_items(self):
		so = create_salad_sales_order()
		self.assertEqual(so.docstatus, 1)

		bom_items = so.get("bom_item")
		self.assertTrue(len(bom_items) > 0)

		child_codes = [d.item_code for d in bom_items]
		self.assertIn("PR-AV-KL", child_codes)
		self.assertIn("PR-LV-CO", child_codes)
		self.assertIn("PR-AV-DRE", child_codes)

		for d in bom_items:
			self.assertEqual(d.parent_item, SALAD_ITEM)

	def test_02_lead_time_rejection(self):
		frappe.db.set_value("BOM Item", {"parent": BOM_NAME, "item_code": "PR-AV-KL"}, "lead_time_days", 60)

		so = frappe.new_doc("Sales Order")
		so.company = COMPANY
		so.customer = CUSTOMER
		so.po_no = f"TEST-LT-{random_string(6)}"
		so.taxes_and_charges = TAX_TEMPLATE
		so.delivery_date = add_days(nowdate(), 5)
		so.append("items", {
			"item_code": SALAD_ITEM,
			"qty": 1,
			"rate": 100,
			"uom": "Kg",
			"warehouse": WAREHOUSE,
			"delivery_date": add_days(nowdate(), 5),
		})
		so.set_taxes()
		so.flags.ignore_permissions = True

		self.assertRaises(frappe.exceptions.ValidationError, so.insert)

		frappe.db.set_value("BOM Item", {"parent": BOM_NAME, "item_code": "PR-AV-KL"}, "lead_time_days", 0)

	def test_03_work_order_for_child_items(self):
		so = create_salad_sales_order()

		bom_items = so.get("bom_item")
		work_orders = []
		for d in bom_items:
			if not d.bom_no:
				continue
			wo = frappe.new_doc("Work Order")
			wo.production_item = d.item_code
			wo.bom_no = d.bom_no
			wo.qty = d.qty
			wo.gross_weight = d.qty
			wo.company = COMPANY
			wo.wip_warehouse = WIP_WAREHOUSE
			wo.fg_warehouse = WAREHOUSE
			wo.sales_order_no = so.name
			wo.is_salad_item = 1
			wo.use_multi_level_bom = 0
			wo.flags.ignore_permissions = True
			wo.flags.ignore_mandatory = True
			wo.flags.ignore_syncing = True
			wo.insert()
			wo.submit()
			work_orders.append(wo)

		self.assertTrue(len(work_orders) > 0)
		for wo in work_orders:
			self.assertEqual(wo.docstatus, 1)

	def test_04_manufacture_stock_entry(self):
		so = create_salad_sales_order()

		bom_items = so.get("bom_item")
		for d in bom_items:
			if not d.bom_no:
				continue
			wo = frappe.new_doc("Work Order")
			wo.production_item = d.item_code
			wo.bom_no = d.bom_no
			wo.qty = d.qty
			wo.gross_weight = d.qty
			wo.company = COMPANY
			wo.wip_warehouse = WIP_WAREHOUSE
			wo.fg_warehouse = WAREHOUSE
			wo.sales_order_no = so.name
			wo.is_salad_item = 1
			wo.use_multi_level_bom = 0
			wo.flags.ignore_permissions = True
			wo.flags.ignore_mandatory = True
			wo.flags.ignore_syncing = True
			wo.insert()
			wo.submit()

			se = frappe.get_doc(make_stock_entry_for_wo(wo.name))
			se.flags.ignore_permissions = True
			se.flags.ignore_mandatory = True
			se.flags.ignore_syncing = True
			se.insert()
			se.submit()

			self.assertEqual(se.docstatus, 1)
			self.assertEqual(se.stock_entry_type, "Manufacture")

	def test_05_delivery_note_from_so(self):
		so = create_salad_sales_order()

		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		dn = make_delivery_note(so.name)
		dn.flags.ignore_permissions = True
		dn.flags.ignore_mandatory = True
		dn.flags.ignore_syncing = True
		dn.insert()
		dn.submit()

		self.assertEqual(dn.docstatus, 1)
		self.assertEqual(dn.items[0].item_code, SALAD_ITEM)
		self.assertEqual(dn.items[0].against_sales_order, so.name)


def create_salad_sales_order(qty=1, delivery_days=30):
	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = CUSTOMER
	so.po_no = f"TEST-SALAD-{random_string(6)}"
	so.taxes_and_charges = TAX_TEMPLATE
	so.delivery_date = add_days(nowdate(), delivery_days)
	so.append("items", {
		"item_code": SALAD_ITEM,
		"qty": qty,
		"rate": 100,
		"uom": "Kg",
		"warehouse": WAREHOUSE,
		"delivery_date": add_days(nowdate(), delivery_days),
	})
	so.set_taxes()
	so.flags.ignore_permissions = True
	so.flags.ignore_syncing = True
	so.insert()
	so.submit()
	return so


def make_stock_entry_for_wo(work_order):
	from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
	se = make_stock_entry(work_order, "Manufacture", qty=None)
	return se
