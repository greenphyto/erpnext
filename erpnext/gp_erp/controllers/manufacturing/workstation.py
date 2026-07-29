import frappe
from frappe import _
from frappe.utils import flt
import re

from erpnext.manufacturing.doctype.workstation.workstation import Workstation


class WorkstationGP(Workstation):
    def autoname(self):
        name = ""
        if self.item_code:
            if not self.operation:
                frappe.throw(_("Operation needed if set item code value"))
            name = f"Farm-{self.item_code}-{self.operation}"
        else:
            if not self.workstation_name:
                frappe.throw(_("Please set workstation name"))
            name = self.workstation_name

        existing_wss = frappe.get_all(
            "Workstation", filters={
                "item_code": self.item_code,
                "operation": self.operation,
                "amended_from": ["is", "not set"]
            }, pluck="name"
        )
        if existing_wss:
            index = self.get_next_version_index(existing_wss)
        else:
            index = 1
        suffix = "%.3i" % index
        ws_name = f"{name}-{suffix}"
        if frappe.db.exists("Workstation", name):
            conflicting_ws = frappe.get_doc("Workstation", name)
            if conflicting_ws.item_code != self.item_code:
                msg = _("A Workstation with name {0} already exists for item {1} and operation {2}.").format(
                    frappe.bold(name), frappe.bold(conflicting_ws.item_code), frappe.bold(conflicting_ws.operation)
                )
                frappe.throw(
                    _("{0}{1} Did you rename the item? Please contact Administrator / Tech support").format(msg, "<br>")
                )
        self.name = ws_name
        self.version = index

    @staticmethod
    def get_next_version_index(existing_ws):
        delimiters = ["/", "-"]
        pattern = "|".join(map(re.escape, delimiters))
        ws_parts = [re.split(pattern, ws_name) for ws_name in existing_ws]
        valid_ws_parts = list(filter(lambda x: len(x) > 1 and x[-1], ws_parts))
        if valid_ws_parts:
            indexes = []
            for part in valid_ws_parts:
                temp = cint(part[-1])
                if len(str(temp)) > 3:
                    temp = cint(str(temp)[len(str(temp)) - 3:])
                indexes.append(temp)
            index = max(indexes) + 1
        else:
            index = 1
        if existing_ws and index == 1:
            index += 1
        return index

    def validate(self):
        self.set_version_missing()
        self.validate_per_kg()
        self.validate_calculation_type()
        self.set_hour_rate()

    def set_version_missing(self):
        if not self.version:
            self.version = 1

    def set_hour_rate(self):
        self.hour_rate = (
            flt(self.hour_rate_labour)
            + flt(self.hour_rate_electricity)
            + flt(self.hour_rate_consumable)
            + flt(self.hour_rate_rent)
        )
        self.per_qty_rate = (
            flt(self.per_qty_rate_electricity)
            + flt(self.per_qty_rate_wages)
            + flt(self.per_qty_rate_machinery)
            + flt(self.per_qty_rate_consumable)
        )

    def validate_per_kg(self):
        if self.item_code and self.calculation_type == "Per KG":
            stock_uom = frappe.get_value("Item", self.item_code, "stock_uom")
            if stock_uom != "Kg":
                frappe.throw(_("<b>Per KG</b> calculation only for Item with default uom as <b>Kg</b>"))

    def validate_calculation_type(self):
        if self.calculation_type in ("Per Qty", "Per KG"):
            self.hour_rate = 0
            self.hour_rate_labour = 0
            self.hour_rate_electricity = 0
            self.hour_rate_consumable = 0
            self.hour_rate_rent = 0
        else:
            self.per_qty_rate = 0
            self.per_qty_rate_electricity = 0
            self.per_qty_rate_wages = 0
            self.per_qty_rate_machinery = 0
