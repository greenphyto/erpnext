import frappe
from frappe import _
from frappe.utils import flt

from erpnext.manufacturing.doctype.routing.routing import Routing


class RoutingGP(Routing):
    def calculate_operating_cost(self):
        for operation in self.operations:
            if not operation.operation_rate:
                if operation.calculation_type == "Per Qty":
                    operation.operation_rate = frappe.db.get_value("Workstation", operation.workstation, "per_qty_rate")
                else:
                    operation.operation_rate = frappe.db.get_value("Workstation", operation.workstation, "hour_rate")
            if operation.calculation_type == "Per Qty":
                operation.operating_cost = flt(operation.operation_rate)
            else:
                operation.operating_cost = flt(
                    flt(operation.operation_rate) * flt(operation.time_in_mins) / 60,
                    operation.precision("operating_cost"),
                )
