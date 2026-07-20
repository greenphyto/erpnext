import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.batch_location.batch_location import (
	decrease_batch_location,
	get_batch_location_qty,
	increase_batch_location,
)
from erpnext.stock.doctype.item.test_item import make_item


def _get_default_company():
	return frappe.db.get_value("Company", {}, "name")


def _get_test_warehouse_group(company):
	group = frappe.db.get_value(
		"Warehouse",
		{"company": company, "is_group": 1, "parent_warehouse": ("is", "not set")},
		"name",
	)
	if not group:
		group = frappe.db.get_value(
			"Warehouse",
			{"company": company, "is_group": 1},
			"name",
		)
	return group


def _make_warehouse(code):
	company = _get_default_company()
	abbr = frappe.db.get_value("Company", company, "abbr")
	wname = "BLTest-{}-{}".format(code, abbr)
	if frappe.db.exists("Warehouse", wname):
		return wname
	w = frappe.new_doc("Warehouse")
	w.warehouse_name = wname
	w.parent_warehouse = _get_test_warehouse_group(company)
	w.company = company
	w.warehouse_code = code
	w.insert(ignore_permissions=True)
	return w.name


def _make_location(warehouse, aisle="A01", bay="B01", level="L01", mixed=1):
	code = frappe.db.get_value("Warehouse", warehouse, "warehouse_code")
	lname = "{}-{}-{}-{}".format(code, aisle, bay, level)
	if frappe.db.exists("Warehouse Location", lname):
		return lname
	loc = frappe.get_doc(
		{
			"doctype": "Warehouse Location",
			"warehouse": warehouse,
			"aisle_row": aisle,
			"bay_column": bay,
			"level_tier": level,
			"is_mixed_storage_allowed": mixed,
			"status": "Available",
		}
	).insert(ignore_permissions=True)
	return loc.name


def _make_item():
	count = frappe.utils.cint(
		frappe.db.sql(
			"select count(*) from `tabItem` where item_code like 'BLItem-%'"
		)[0][0]
	)
	item_code = "BLItem-{}".format(count)
	if frappe.db.exists("Item", item_code):
		return item_code
	return make_item(
		item_code, {"has_batch_no": 1, "create_new_batch": 1, "is_stock_item": 1}
	).name


def _make_batch(item_code):
	count = frappe.utils.cint(
		frappe.db.sql(
			"select count(*) from `tabBatch` where batch_id like 'BLBatch-%'"
		)[0][0]
	)
	batch_id = "BLBatch-{}".format(count)
	batch = frappe.new_doc("Batch")
	batch.batch_id = batch_id
	batch.item = item_code
	batch.insert(ignore_permissions=True)
	return batch.name


def _set_default_warehouse(warehouse):
	frappe.db.set_single_value("Warehouse Location Settings", "default_warehouse", warehouse)
	frappe.clear_cache()


def _cleanup():
	frappe.db.sql("delete from `tabBatch Location` where batch like 'BLBatch-%'")
	frappe.db.sql(
		"delete from `tabWarehouse Location` where warehouse in (select name from `tabWarehouse` where warehouse_name like 'BLTest-%')"
	)
	frappe.db.sql("delete from `tabWarehouse` where warehouse_name like 'BLTest-%'")
	frappe.db.sql("delete from `tabItem` where item_code like 'BLItem-%'")
	frappe.db.sql("delete from `tabBatch` where batch_id like 'BLBatch-%'")
	frappe.db.commit()


class TestBatchLocation(FrappeTestCase):
	def setUp(self):
		_cleanup()
		self.warehouse = _make_warehouse("FG")
		_set_default_warehouse(self.warehouse)
		self.location = _make_location(self.warehouse)
		self.item = _make_item()
		self.batch = _make_batch(self.item)

	def tearDown(self):
		frappe.db.set_single_value("Warehouse Location Settings", "default_warehouse", "")
		frappe.db.commit()
		_cleanup()

	def test_increase_and_decrease_use_stock_qty(self):
		increase_batch_location(self.batch, self.location, 12, "Kg", 1)
		self.assertEqual(
			get_batch_location_qty(self.batch, self.location), 12
		)
		decrease_batch_location(self.batch, self.location, 5)
		self.assertEqual(
			get_batch_location_qty(self.batch, self.location), 7
		)

	def test_decrease_rejects_negative_result(self):
		increase_batch_location(self.batch, self.location, 4, "Kg", 1)
		self.assertRaises(
			ValidationError,
			decrease_batch_location,
			self.batch,
			self.location,
			5,
		)

	def test_increase_creates_row_if_missing(self):
		self.assertFalse(
			frappe.db.exists(
				"Batch Location",
				{"batch": self.batch, "warehouse_location": self.location},
			)
		)
		increase_batch_location(self.batch, self.location, 10, "Kg", 1)
		self.assertTrue(
			frappe.db.exists(
				"Batch Location",
				{"batch": self.batch, "warehouse_location": self.location},
			)
		)

	def test_zero_qty_row_deleted(self):
		increase_batch_location(self.batch, self.location, 10, "Kg", 1)
		decrease_batch_location(self.batch, self.location, 10)
		self.assertFalse(
			frappe.db.exists(
				"Batch Location",
				{"batch": self.batch, "warehouse_location": self.location},
			)
		)

	def test_non_mixed_location_rejects_another_batch(self):
		non_mixed_loc = _make_location(
			self.warehouse, aisle="A02", bay="B01", level="L01", mixed=0
		)
		second_batch = _make_batch(self.item)
		increase_batch_location(
			self.batch, non_mixed_loc, 4, "Kg", 1
		)
		self.assertRaises(
			ValidationError,
			increase_batch_location,
			second_batch,
			non_mixed_loc,
			1,
			"Kg",
			1,
		)

	def test_blocked_location_rejects_increase(self):
		frappe.db.set_value("Warehouse Location", self.location, "status", "Blocked")
		frappe.clear_cache()
		self.assertRaises(
			ValidationError,
			increase_batch_location,
			self.batch,
			self.location,
			5,
			"Kg",
			1,
		)

	def test_disabled_location_rejects_increase(self):
		frappe.db.set_value("Warehouse Location", self.location, "disabled", 1)
		frappe.clear_cache()
		self.assertRaises(
			ValidationError,
			increase_batch_location,
			self.batch,
			self.location,
			5,
			"Kg",
			1,
		)

	def test_direct_save_rejected(self):
		row = frappe.get_doc(
			{
				"doctype": "Batch Location",
				"batch": self.batch,
				"item": self.item,
				"warehouse_location": self.location,
				"warehouse": self.warehouse,
				"qty": 10,
				"stock_uom": frappe.db.get_value("Item", self.item, "stock_uom"),
			}
		)
		self.assertRaises(ValidationError, row.insert, ignore_permissions=True)

	def test_stock_qty_drives_balance(self):
		increase_batch_location(self.batch, self.location, 10, "Kg", 1)
		self.assertEqual(
			get_batch_location_qty(self.batch, self.location), 10
		)
