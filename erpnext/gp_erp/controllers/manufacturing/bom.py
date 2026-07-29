import frappe
from frappe import _
from frappe.utils import cint, cstr, flt
from frappe.model.naming import parse_naming_series

from erpnext.manufacturing.doctype.bom.bom import BOM


class BOMGP(BOM):
    def before_naming(self):
        if getattr(self, "amended_from", None):
            self.flags.skip_amend_name = 1

    def autoname(self):
        prefix = self.doctype
        suffix = cstr(cint(self.operation_no))
        bom_name = f"{prefix}-{self.item}-{suffix}"
        existing_boms = frappe.get_all(
            "BOM", filters={"name": ['like', "%%" + bom_name + "%%"]}, pluck="name"
        )
        if existing_boms:
            index = self.get_next_version_index(existing_boms)
        else:
            index = 1
        suffix_index = "%.3i" % index
        bom_name = bom_name + suffix_index
        if len(bom_name) <= 136:
            name = bom_name
        else:
            truncated_length = 136 - (len(prefix) + len(suffix) + 2)
            truncated_item_name = self.item[:truncated_length]
            truncated_item_name = truncated_item_name.rsplit(" ", 1)[0]
            name = f"{prefix}-{truncated_item_name}-{suffix}"
        count = frappe.db.count('BOM', {'name': ['like', f'{name}%%']})
        if count > 1:
            name += f"-{count - 1}"
        if frappe.db.exists("BOM", name):
            conflicting_bom = frappe.get_doc("BOM", name)
            msg = _("A BOM with name {0} already exists for item {1} with operation {2}.").format(
                frappe.bold(name), frappe.bold(conflicting_bom.item), frappe.bold(conflicting_bom.operation_no)
            )
            frappe.throw(
                _("{0}{1} Did you rename the item? Please contact Administrator / Tech support").format(
                    msg, "<br>"
                )
            )
        self.name = name

    def get_next_version_index(self, existing_boms):
        valid_bom_parts = [bom_string.split("-") for bom_string in existing_boms]
        if valid_bom_parts:
            indexes = []
            for part in valid_bom_parts:
                temp = cint(part[-1])
                if len(str(temp)) > 3:
                    temp = cint(str(temp)[len(str(temp)) - 3:])
                indexes.append(temp)
            index = max(indexes) + 1
        else:
            index = 1
        return index

    def control_salad_recipe(self):
        if not cint(frappe.get_value("Item", self.item, "salad_product")):
            return
        self.rm_cost_as_per = "Last Purchase Rate"
        self.storage_duration = cint(self.storage_duration) or 14
        for d in self.items:
            d.do_not_explode = 1

    def get_routing(self):
        if self.routing:
            self.fetch_exploded = 0
            routing_fields = [
                "sequence_id",
                "operation",
                "workstation",
                "description",
                "time_in_mins",
                "batch_size",
                "operating_cost",
                "idx",
                "calculation_type",
                "operation_rate",
                "set_cost_based_on_bom_qty",
                "fixed_time",
            ]
            for row in frappe.get_all(
                "Routing",
                filters={"parent": self.routing},
                fields=routing_fields,
                order_by="sequence_id, idx",
            ):
                child = self.append("operations", row)
                child.operation_rate = flt(row.operation_rate / self.conversion_rate, child.precision("operation_rate"))

    def get_workstation_cost(self):
        for d in self.get("operations"):
            if d.workstation:
                doc = frappe.get_doc("Workstation", d.workstation)
                if doc.calculation_type in ("Per KG", "Per Qty"):
                    d.electrical_cost = doc.per_qty_rate_electricity
                    d.consumable_cost = doc.per_qty_rate_consumable
                    d.machinery_cost = doc.per_qty_rate_machinery
                    d.wages_cost = doc.per_qty_rate_wages
                    d.rent_cost = 0
                else:
                    d.electrical_cost = doc.hour_rate_electricity
                    d.consumable_cost = doc.hour_rate_consumable
                    d.machinery_cost = 0
                    d.wages_cost = doc.hour_rate_labour
                    d.rent_cost = doc.hour_rate_rent

    def calculate_cost(self, update_hour_rate=False):
        self.get_workstation_cost()
        self.calculate_operating_cost(update_hour_rate)
        self.calculate_bom_cost()

    def calculate_operating_cost(self, update_hour_rate=False):
        for d in self.get("operations"):
            if d.workstation:
                self.update_rate_and_time(d, update_hour_rate)
            if d.calculation_type == "Per Hour":
                operating_cost = d.operating_cost
                base_operating_cost = d.base_operating_cost
            else:
                operating_cost = flt(d.operating_cost) * flt(self.quantity)
                base_operating_cost = flt(d.base_operating_cost) * flt(self.quantity)
            self.operating_cost += flt(operating_cost)
            self.base_operating_cost += flt(base_operating_cost)

    def update_rate_and_time(self, row, update_hour_rate=False):
        operation_rate = 0
        self.get_workstation_cost()
        if not row.operation_rate or update_hour_rate:
            if row.calculation_type in ("Per Qty", "Per KG"):
                operation_rate = flt(frappe.get_cached_value("Workstation", row.workstation, "per_qty_rate"))
            else:
                operation_rate = flt(frappe.get_cached_value("Workstation", row.workstation, "hour_rate"))
        if operation_rate:
            row.operation_rate = (
                operation_rate / flt(self.conversion_rate) if self.conversion_rate and operation_rate else operation_rate
            )
            row.base_operation_rate = row.operation_rate
        if row.operation_rate and row.time_in_mins:
            row.base_hour_rate = flt(row.operation_rate) * flt(self.conversion_rate)
            if row.calculation_type in ("Per Qty", "Per KG"):
                row.operating_cost = flt(row.operation_rate) * flt(self.quantity)
            else:
                row.operating_cost = flt(row.operation_rate) * flt(row.time_in_mins) / 60.0
            row.base_operating_cost = flt(row.operating_cost) * flt(self.conversion_rate)
            row.cost_per_unit = row.operating_cost / (row.batch_size or 1.0)
            row.base_cost_per_unit = row.base_operating_cost / (row.batch_size or 1.0)
