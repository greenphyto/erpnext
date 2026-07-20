import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.doctype.warehouse_location_settings.warehouse_location_settings import (
	get_default_warehouse,
)


def _set_default_warehouse(warehouse):
	frappe.db.set_single_value("Warehouse Location Settings", "default_warehouse", warehouse)
	frappe.clear_cache()


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


def _make_test_warehouse(code):
	company = _get_default_company()
	abbr = frappe.db.get_value("Company", company, "abbr")
	wname = "WLoc-{}-{} - {}".format(
		code,
		frappe.utils.cint(
			frappe.db.sql(
				"select count(*) from `tabWarehouse` where warehouse_name like 'WLoc-%'"
			)[0][0]
		),
		abbr,
	)
	if frappe.db.exists("Warehouse", wname):
		return wname
	w = frappe.new_doc("Warehouse")
	w.warehouse_name = wname
	w.parent_warehouse = _get_test_warehouse_group(company)
	w.company = company
	w.warehouse_code = code
	w.insert(ignore_permissions=True)
	return w.name


def _make_test_item():
	count = frappe.utils.cint(
		frappe.db.sql(
			"select count(*) from `tabItem` where item_code like 'WLocItem-%'"
		)[0][0]
	)
	item_code = "WLocItem-{}".format(count)
	if frappe.db.exists("Item", item_code):
		return item_code
	return make_item(
		item_code, {"has_batch_no": 1, "create_new_batch": 1, "is_stock_item": 1}
	).name


def _make_test_batch(item_code):
	count = frappe.utils.cint(
		frappe.db.sql(
			"select count(*) from `tabBatch` where batch_id like 'WLocBatch-%'"
		)[0][0]
	)
	batch_name = "WLocBatch-{}".format(count)
	batch = frappe.new_doc("Batch")
	batch.batch_id = batch_name
	batch.item = item_code
	batch.insert(ignore_permissions=True)
	return batch.name


class TestWarehouseLocationSchema(FrappeTestCase):
	def assert_field(self, meta, fieldname, **expected):
		field = meta.get_field(fieldname)
		self.assertIsNotNone(field, f"{meta.name}.{fieldname} is missing")
		for attribute, value in expected.items():
			self.assertEqual(
				getattr(field, attribute),
				value,
				f"Unexpected {attribute} for {meta.name}.{fieldname}",
			)

	def assert_permissions(self, meta, expected):
		permissions = {permission.role: permission for permission in meta.permissions}
		self.assertTrue(
			set(expected).issubset(permissions),
			f"Missing permission roles for {meta.name}: {set(expected) - set(permissions)}",
		)
		for role, flags in expected.items():
			for flag, value in flags.items():
				self.assertEqual(
					permissions[role].get(flag, 0),
					value,
					f"Unexpected {flag} permission for {meta.name}/{role}",
				)

	def test_required_doctypes_and_fields_exist(self):
		settings = frappe.get_meta("Warehouse Location Settings")
		location = frappe.get_meta("Warehouse Location")
		action = frappe.get_meta("Warehouse Action")
		batch_location = frappe.get_meta("Batch Location")
		warehouse = frappe.get_meta("Warehouse")

		for meta in (settings, location, action, batch_location):
			self.assertTrue(meta)

		self.assert_field(
			warehouse,
			"warehouse_code",
			fieldtype="Data",
			label="Warehouse Code",
		)

		self.assert_field(
			settings,
			"default_warehouse",
			fieldtype="Link",
			label="Default Warehouse",
			options="Warehouse",
			reqd=1,
		)

		for fieldname in ("location_code", "aisle_row", "bay_column", "level_tier"):
			self.assert_field(location, fieldname, fieldtype="Data", reqd=1)
		self.assert_field(
			location,
			"warehouse",
			fieldtype="Link",
			options="Warehouse",
			reqd=1,
		)
		self.assert_field(
			location,
			"status",
			fieldtype="Select",
			options="Available\nOccupied\nPartial\nBlocked",
		)
		self.assert_field(
			location,
			"is_mixed_storage_allowed",
			fieldtype="Check",
			default="1",
		)
		self.assert_field(location, "disabled", fieldtype="Check", default="0")

		self.assertEqual(action.is_submittable, 1)
		self.assert_field(
			action,
			"naming_series",
			fieldtype="Select",
			options="WHA-.YYYY.-",
			reqd=1,
		)
		self.assert_field(
			action,
			"action_type",
			fieldtype="Select",
			options="New\nMove\nDiscard",
			reqd=1,
		)
		for fieldname in ("posting_datetime", "batch", "qty", "uom", "conversion_factor"):
			self.assertEqual(action.get_field(fieldname).reqd, 1)
		self.assertEqual(action.get_field("batch").options, "Batch")
		for fieldname in ("item", "warehouse", "stock_uom", "stock_qty", "user"):
			self.assertEqual(action.get_field(fieldname).read_only, 1)

		for fieldname in ("batch", "item", "warehouse_location", "warehouse", "qty", "stock_uom"):
			self.assertEqual(batch_location.get_field(fieldname).reqd, 1)
		for fieldname in (
			"item",
			"warehouse",
			"qty",
			"stock_uom",
			"uom",
			"conversion_factor",
			"last_updated",
		):
			self.assertEqual(batch_location.get_field(fieldname).read_only, 1)

		self.assert_permissions(
			settings,
			{
				"All": {"read": 1},
				"Stock Manager": {"read": 1, "write": 1},
			},
		)
		self.assert_permissions(
			location,
			{
				"All": {"read": 1},
				"Stock Manager": {"read": 1, "write": 1, "create": 1, "delete": 1},
			},
		)
		self.assert_permissions(
			action,
			{
				"Stock User": {"read": 1, "create": 1, "submit": 1, "cancel": 1, "delete": 0},
				"Stock Manager": {
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
					"submit": 1,
					"cancel": 1,
					"amend": 1,
				},
			},
		)
		self.assert_permissions(
			batch_location,
			{
				"All": {"read": 1},
				"Stock Manager": {"read": 1, "write": 1, "create": 0, "delete": 0},
			},
		)

	def _cleanup_locations(self):
		frappe.db.sql(
			"delete from `tabWarehouse Location` where warehouse in (select name from `tabWarehouse` where warehouse_name like 'WLoc-%')"
		)
		frappe.db.sql(
			"delete from `tabWarehouse` where warehouse_name like 'WLoc-%'"
		)
		frappe.db.sql(
			"delete from `tabItem` where item_code like 'WLocItem-%'"
		)
		frappe.db.sql(
			"delete from `tabBatch` where batch_id like 'WLocBatch-%'"
		)
		frappe.db.commit()

	def setUp(self):
		self._cleanup_locations()

	def tearDown(self):
		frappe.db.set_single_value("Warehouse Location Settings", "default_warehouse", "")
		frappe.db.commit()
		self._cleanup_locations()

	def test_location_code_uses_warehouse_code(self):
		warehouse = _make_test_warehouse("FG")
		_set_default_warehouse(warehouse)
		location = frappe.get_doc(
			{
				"doctype": "Warehouse Location",
				"warehouse": warehouse,
				"aisle_row": "A01",
				"bay_column": "B03",
				"level_tier": "L02",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(location.name, "FG-A01-B03-L02")

	def test_location_rejects_non_default_warehouse(self):
		default = _make_test_warehouse("FG")
		other = _make_test_warehouse("OT")
		_set_default_warehouse(default)
		self.assertRaises(
			ValidationError,
			lambda: frappe.get_doc(
				{
					"doctype": "Warehouse Location",
					"warehouse": other,
					"aisle_row": "A01",
					"bay_column": "B01",
					"level_tier": "L01",
				}
			).insert(ignore_permissions=True),
		)

	def test_location_requires_warehouse_code(self):
		warehouse = _make_test_warehouse("NOCODE")
		frappe.db.set_value("Warehouse", warehouse, "warehouse_code", "")
		_set_default_warehouse(warehouse)
		self.assertRaises(
			ValidationError,
			lambda: frappe.get_doc(
				{
					"doctype": "Warehouse Location",
					"warehouse": warehouse,
					"aisle_row": "A01",
					"bay_column": "B01",
					"level_tier": "L01",
				}
			).insert(ignore_permissions=True),
		)

	def test_duplicate_coordinates_rejected(self):
		warehouse = _make_test_warehouse("FG")
		_set_default_warehouse(warehouse)
		frappe.get_doc(
			{
				"doctype": "Warehouse Location",
				"warehouse": warehouse,
				"aisle_row": "A01",
				"bay_column": "B01",
				"level_tier": "L01",
			}
		).insert(ignore_permissions=True)
		self.assertRaises(
			Exception,
			lambda: frappe.get_doc(
				{
					"doctype": "Warehouse Location",
					"warehouse": warehouse,
					"aisle_row": "A01",
					"bay_column": "B01",
					"level_tier": "L01",
				}
			).insert(ignore_permissions=True),
		)

	def test_settings_rejects_disabled_default_warehouse(self):
		warehouse = _make_test_warehouse("DIS")
		_set_default_warehouse(warehouse)
		frappe.db.set_value("Warehouse", warehouse, "disabled", 1)
		frappe.clear_cache()
		settings = frappe.get_doc("Warehouse Location Settings")
		self.assertRaises(ValidationError, settings.save)
