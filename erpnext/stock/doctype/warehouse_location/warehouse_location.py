import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.stock.doctype.warehouse_location_settings.warehouse_location_settings import (
	get_default_warehouse,
	validate_default_warehouse,
)


class WarehouseLocation(Document):
	def autoname(self):
		if not self.warehouse:
			frappe.throw(_("Warehouse is required."))
		warehouse_code = frappe.db.get_value("Warehouse", self.warehouse, "warehouse_code")
		if not warehouse_code:
			frappe.throw(
				_("Set Warehouse Code on Warehouse {0} before creating locations.").format(self.warehouse)
			)
		self.name = "-".join((warehouse_code, self.aisle_row, self.bay_column, self.level_tier))
		self.location_code = self.name

	def validate(self):
		validate_default_warehouse(self.warehouse)
		for fieldname in ("aisle_row", "bay_column", "level_tier"):
			if not self.get(fieldname):
				frappe.throw(_("{0} is required.").format(self.meta.get_label(fieldname)))
		self.validate_unique_coordinates()

	def validate_unique_coordinates(self):
		filters = {
			"warehouse": self.warehouse,
			"aisle_row": self.aisle_row,
			"bay_column": self.bay_column,
			"level_tier": self.level_tier,
		}
		if self.name:
			filters["name"] = ["!=", self.name]
		if frappe.db.exists("Warehouse Location", filters):
			frappe.throw(
				_("A Warehouse Location with the same warehouse, aisle, bay, and level already exists.")
			)
