import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, getdate, get_link_to_form
from frappe.model.naming import parse_naming_series
from erpnext.accounts.utils import get_company_default

from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
from erpnext.stock.stock_ledger import get_valuation_rate


class WorkOrderGP(WorkOrder):
    def autoname(self):
        if cint(self.operation_no):
            alpha_map = ["A", "B", "C", "D", "E", "F"]
            alpha = alpha_map[cint(self.operation_no) - 1]
            if self.foms_lot_name:
                series = self.foms_lot_name + "-.###.-{}".format(alpha)
            else:
                series = self.naming_series + ".###.-{}".format(alpha)
        else:
            if self.foms_lot_name:
                series = self.foms_lot_name + "-.###"
            else:
                series = self.naming_series + ".###"
        self.name = parse_naming_series(series, doc=self)

    def set_default_warehouse(self):
        super(WorkOrderGP, self).set_default_warehouse()
        if not self.source_warehouse:
            self.source_warehouse = frappe.db.get_single_value("Manufacturing Settings", "default_source_warehouse")

    def validate_non_stock_items(self):
        is_stock_item = {}
        remove_list = []
        for d in self.get("required_items"):
            stock_item = 0
            if not d.item_code in is_stock_item:
                stock_item = frappe.get_value("Item", d.item_code, "is_stock_item")
                is_stock_item[d.item_code] = stock_item
            else:
                stock_item = is_stock_item[d.item_code]
            if not stock_item:
                remove_list.append(d)
        for d in remove_list:
            self.remove(d)

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

    def calculate_operating_cost(self):
        self.planned_operating_cost, self.actual_operating_cost = 0.0, 0.0
        planned_qty = self.gross_weight
        actual_qty = self.gross_weight
        for d in self.get("operations"):
            if d.calculation_type == "Per Hour":
                d.planned_operating_cost = flt(d.operation_rate) * (flt(d.time_in_mins) / 60.0)
                d.actual_operating_cost = flt(d.operation_rate) * (flt(d.actual_operation_time) / 60.0)
            else:
                d.planned_operating_cost = flt(d.operation_rate) * (flt(planned_qty))
                d.actual_operating_cost = flt(d.operation_rate) * (flt(actual_qty))
            self.planned_operating_cost += flt(d.planned_operating_cost)
            self.actual_operating_cost += flt(d.actual_operating_cost)

    def validate_cost_editing(self):
        old_doc = self.get_doc_before_save()
        if not old_doc:
            return
        cost_fields = ['electrical_cost', 'consumable_cost', 'machinery_cost', 'wages_cost', 'rent_cost']
        for d in self.get("operations"):
            total_rate = 0
            edit = False
            row = old_doc.get("operations", {"name": d.name})
            if row:
                row = row[0]
            else:
                continue
            for field in cost_fields:
                if d.get(field) != row.get(field):
                    edit = True
                total_rate += flt(d.get(field))
            if edit and flt(d.completed_qty) != 0:
                frappe.throw(_(f"Cannot editing cost for completed operation <b>{d.operation}</b>"))
            d.operation_rate = total_rate

    def write_opr_version(self):
        for d in self.get("operations"):
            if d.enable_cost_editing:
                d.version = "Custom"
            else:
                d.version = frappe.get_value("Workstation", d.workstation, "version") or 1

    def update_sales_order(self, state="Start"):
        if not self.sales_order_no:
            return

        def _get_sales_order():
            return [cstr(x).strip() for x in self.sales_order_no.split(",")]

        so_list = _get_sales_order()
        for d in so_list:
            doc = frappe.get_doc("Sales Order", d)
            if state == "Start":
                doc.update_work_order_reference(self.name, self.production_item)
            elif state == "Finish":
                doc.update_work_progress(self.production_item, self.qty)
            doc.db_update()

    def set_packet_size(self):
        data = []
        if self.sales_order_no:
            doc_name = self.sales_order_no.replace(" ", "").split(",")
            temp = frappe.db.sql("select uom, conversion_factor from `tabSales Order Item` where parent in %(parent)s and item_code = %(item_code)s",
                                 {"parent": doc_name, "item_code": self.production_item}, as_dict=1)
            if temp:
                data += temp
        if self.request_no:
            doc_name = self.request_no.replace(" ", "").split(",")
            temp = frappe.db.sql("select uom, unit_weight as conversion_factor from `tabRequest Items` where parent in %(parent)s and item_code = %(item_code)s",
                                 {"parent": doc_name, "item_code": self.production_item}, as_dict=1)
            if temp:
                data += temp
        res = frappe.db.sql('select packaging, weight, package_item from `tabPackaging List Available` where parent = %s and parentfield = "packaging" and `default` = 1', (self.production_item), as_dict=1)
        if res and len(res) == 1:
            self.packet_size = res[0].packaging
            self.conversion_factor = res[0].weight
            self.flags.package_item = res[0].package_item
        else:
            self.packet_size = frappe.db.get_value("Item", self.production_item, "stock_uom")
            self.conversion_factor = 1

    def get_packaging_from_order(self):
        total_pcs = 0
        if self.sales_order_no:
            doc_name = self.sales_order_no.replace(" ", "").split(",")
            temp = frappe.db.sql("select sum(qty) as qty from `tabSales Order Item` where parent in %(parent)s and item_code = %(item_code)s",
                                 {"parent": doc_name, "item_code": self.production_item}, as_dict=1)
            if temp:
                total_pcs = temp[0].get("qty")
        if self.request_no:
            doc_name = self.request_no.replace(" ", "").split(",")
            temp = frappe.db.sql("select sum(qty) as qty from `tabRequest Items` where parent in %(parent)s and item_code = %(item_code)s",
                                 {"parent": doc_name, "item_code": self.production_item}, as_dict=1)
            if temp:
                total_pcs = temp[0].get("qty")
        if not self.packet_size:
            self.set_packet_size()
        total_pcs = self.qty / flt(self.conversion_factor or 1)
        if not total_pcs:
            return
        default_packaging = frappe.db.get_single_value("Manufacturing Settings", "default_packaging")
        pack_item = self.flags.package_item or default_packaging
        if not pack_item or not self.packet_size:
            return
        source_warehouse = self.source_warehouse
        item = frappe.get_doc("Item", pack_item)
        rate = get_valuation_rate(item.item_code, source_warehouse, "", "")
        self.append(
            "required_items",
            {
                "rate": rate,
                "amount": rate * total_pcs,
                "operation": "Harvesting",
                "item_code": item.item_code,
                "item_name": item.item_name,
                "description": item.description,
                "allow_alternative_item": 0,
                "required_qty": total_pcs,
                "source_warehouse": source_warehouse,
                "is_packaging": 1,
            }
        )

    def set_is_salad_item(self):
        req_list = []
        so_list = []
        if self.request_no:
            req_list = self.request_no.split(", ")
        if self.sales_order_no:
            so_list = self.sales_order_no.split(", ")

        def _valid_order(doctype, doc_name):
            temp = frappe.db.sql("""
                SELECT parent FROM `tabBOM Item`
                WHERE parenttype = %s AND parent = %s AND docstatus = 1
            """, (doctype, doc_name), as_dict=1)
            return temp

        for req in req_list:
            if _valid_order("Request", req):
                self.is_salad_item = 1
        for req in so_list:
            if _valid_order("Sales Order", req):
                self.is_salad_item = 1

    def validate_operation_time(self):
        for d in self.operations:
            if d.calculation_type == "Per Hour" and not d.time_in_mins > 0:
                frappe.throw(_("Operation Time must be greater than 0 for Operation {0}").format(d.operation))
