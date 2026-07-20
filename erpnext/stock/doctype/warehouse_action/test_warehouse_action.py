import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.batch_location.batch_location import get_batch_location_qty
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.warehouse_action.warehouse_action import get_action_context


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
			"Warehouse", {"company": company, "is_group": 1}, "name"
		)
	return group


def _make_warehouse(code):
	company = _get_default_company()
	abbr = frappe.db.get_value("Company", company, "abbr")
	wname = "WHAct-{}-{}".format(code, abbr)
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
			"select count(*) from `tabItem` where item_code like 'WHActItem-%'"
		)[0][0]
	)
	item_code = "WHActItem-{}".format(count)
	if frappe.db.exists("Item", item_code):
		return item_code
	return make_item(
		item_code, {"has_batch_no": 1, "create_new_batch": 1, "is_stock_item": 1}
	).name


def _make_batch(item_code):
	count = frappe.utils.cint(
		frappe.db.sql(
			"select count(*) from `tabBatch` where batch_id like 'WHActBatch-%'"
		)[0][0]
	)
	batch_id = "WHActBatch-{}".format(count)
	batch = frappe.new_doc("Batch")
	batch.batch_id = batch_id
	batch.item = item_code
	batch.insert(ignore_permissions=True)
	return batch.name


def _set_default_warehouse(warehouse):
	frappe.db.set_single_value("Warehouse Location Settings", "default_warehouse", warehouse)
	frappe.clear_cache()


def _seed_batch_location(batch, location, qty):
	from erpnext.stock.doctype.batch_location.batch_location import increase_batch_location

	increase_batch_location(batch, location, qty, "Kg", 1)


def _make_action(action_type, batch, warehouse, qty, uom="Kg", conversion_factor=1,
				 from_location=None, to_location=None):
	return frappe.get_doc(
		{
			"doctype": "Warehouse Action",
			"action_type": action_type,
			"batch": batch,
			"warehouse": warehouse,
			"qty": qty,
			"uom": uom,
			"conversion_factor": conversion_factor,
			"from_location": from_location,
			"to_location": to_location,
		}
	)


def _get_qty(batch, location):
	return get_batch_location_qty(batch, location)


def _cleanup():
	frappe.db.sql("delete from `tabBatch Location` where batch like 'WHActBatch-%'")
	frappe.db.sql(
		"delete from `tabWarehouse Action` where batch like 'WHActBatch-%'"
	)
	frappe.db.sql(
		"delete from `tabWarehouse Location` where warehouse in (select name from `tabWarehouse` where warehouse_name like 'WHAct-%')"
	)
	frappe.db.sql("delete from `tabWarehouse` where warehouse_name like 'WHAct-%'")
	frappe.db.sql("delete from `tabItem` where item_code like 'WHActItem-%'")
	frappe.db.sql("delete from `tabBatch` where batch_id like 'WHActBatch-%'")
	frappe.db.commit()


class TestWarehouseAction(FrappeTestCase):
	def setUp(self):
		_cleanup()
		self.warehouse = _make_warehouse("FG")
		_set_default_warehouse(self.warehouse)
		self.loc_a = _make_location(self.warehouse, "A01", "B01", "L01")
		self.loc_b = _make_location(self.warehouse, "A01", "B02", "L01")
		self.item = _make_item()
		self.batch = _make_batch(self.item)

	def tearDown(self):
		frappe.db.set_single_value("Warehouse Location Settings", "default_warehouse", "")
		frappe.db.commit()
		_cleanup()

	def test_new_submit_and_cancel(self):
		action = _make_action(
			"New", self.batch, self.warehouse, 2, "Kg", 10, to_location=self.loc_a
		)
		action.submit()
		self.assertEqual(_get_qty(self.batch, self.loc_a), 20)
		action.cancel()
		self.assertEqual(_get_qty(self.batch, self.loc_a), 0)

	def test_move_reverses_on_cancel(self):
		_seed_batch_location(self.batch, self.loc_a, 20)
		action = _make_action(
			"Move",
			self.batch,
			self.warehouse,
			1,
			"Kg",
			10,
			from_location=self.loc_a,
			to_location=self.loc_b,
		)
		action.submit()
		self.assertEqual(_get_qty(self.batch, self.loc_a), 10)
		self.assertEqual(_get_qty(self.batch, self.loc_b), 10)
		action.cancel()
		self.assertEqual(_get_qty(self.batch, self.loc_a), 20)
		self.assertEqual(_get_qty(self.batch, self.loc_b), 0)

	def test_discard_is_location_only(self):
		_seed_batch_location(self.batch, self.loc_a, 20)
		action = _make_action(
			"Discard",
			self.batch,
			self.warehouse,
			1,
			"Kg",
			10,
			from_location=self.loc_a,
		)
		action.submit()
		self.assertEqual(_get_qty(self.batch, self.loc_a), 10)

	def test_draft_does_not_change_balance(self):
		action = _make_action(
			"New", self.batch, self.warehouse, 2, "Kg", 10, to_location=self.loc_a
		)
		action.insert()
		self.assertEqual(_get_qty(self.batch, self.loc_a), 0)

	def test_move_same_location_rejected(self):
		_seed_batch_location(self.batch, self.loc_a, 20)
		action = _make_action(
			"Move",
			self.batch,
			self.warehouse,
			1,
			"Kg",
			1,
			from_location=self.loc_a,
			to_location=self.loc_a,
		)
		self.assertRaises(ValidationError, action.insert, ignore_permissions=True)

	def test_insufficient_source_balance_rejected(self):
		_seed_batch_location(self.batch, self.loc_a, 5)
		action = _make_action(
			"Move",
			self.batch,
			self.warehouse,
			10,
			"Kg",
			1,
			from_location=self.loc_a,
			to_location=self.loc_b,
		)
		self.assertRaises(ValidationError, action.submit)

	def test_blocked_location_rejected(self):
		frappe.db.set_value("Warehouse Location", self.loc_a, "status", "Blocked")
		frappe.clear_cache()
		action = _make_action(
			"New", self.batch, self.warehouse, 1, "Kg", 1, to_location=self.loc_a
		)
		self.assertRaises(ValidationError, action.insert, ignore_permissions=True)

	def test_disabled_location_rejected(self):
		frappe.db.set_value("Warehouse Location", self.loc_a, "disabled", 1)
		frappe.clear_cache()
		action = _make_action(
			"New", self.batch, self.warehouse, 1, "Kg", 1, to_location=self.loc_a
		)
		self.assertRaises(ValidationError, action.insert, ignore_permissions=True)

	def test_missing_to_location_for_new_rejected(self):
		action = _make_action("New", self.batch, self.warehouse, 1, "Kg", 1)
		self.assertRaises(ValidationError, action.insert, ignore_permissions=True)

	def test_missing_from_location_for_move_rejected(self):
		action = _make_action(
			"Move", self.batch, self.warehouse, 1, "Kg", 1, to_location=self.loc_b
		)
		self.assertRaises(ValidationError, action.insert, ignore_permissions=True)

	def test_qty_must_be_positive(self):
		action = _make_action(
			"New", self.batch, self.warehouse, -1, "Kg", 1, to_location=self.loc_a
		)
		self.assertRaises(ValidationError, action.insert, ignore_permissions=True)

	def test_conversion_factor_must_be_positive(self):
		action = _make_action(
			"New", self.batch, self.warehouse, 1, "Kg", 0, to_location=self.loc_a
		)
		self.assertRaises(ValidationError, action.insert, ignore_permissions=True)

	def test_server_computes_stock_qty(self):
		action = _make_action(
			"New", self.batch, self.warehouse, 2, "Kg", 5, to_location=self.loc_a
		)
		action.insert()
		self.assertEqual(action.stock_qty, 10)

	def test_get_action_context(self):
		result = get_action_context()
		self.assertEqual(result["warehouse"], self.warehouse)
		self.assertEqual(
			result["warehouse_code"],
			frappe.db.get_value("Warehouse", self.warehouse, "warehouse_code"),
		)

	def test_new_missing_settings_rejected(self):
		frappe.db.set_single_value("Warehouse Location Settings", "default_warehouse", "")
		frappe.clear_cache()
		action = _make_action(
			"New", self.batch, self.warehouse, 1, "Kg", 1, to_location=self.loc_a
		)
		self.assertRaises(Exception, action.insert, ignore_permissions=True)
