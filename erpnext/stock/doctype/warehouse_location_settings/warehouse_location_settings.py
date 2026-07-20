import frappe
from frappe import _


def get_default_warehouse():
	warehouse = frappe.db.get_single_value("Warehouse Location Settings", "default_warehouse")
	if not warehouse:
		frappe.throw(_("Set Default Warehouse in Warehouse Location Settings before using locations."))
	return warehouse


def validate_default_warehouse(warehouse):
	default_warehouse = get_default_warehouse()
	if warehouse != default_warehouse:
		frappe.throw(_("Warehouse Location must use the configured Default Warehouse {0}.").format(default_warehouse))
	return default_warehouse


class WarehouseLocationSettings(frappe.model.document.Document):
	def validate(self):
		if self.default_warehouse and frappe.db.get_value("Warehouse", self.default_warehouse, "disabled"):
			frappe.throw(_("Default Warehouse cannot be disabled."))
