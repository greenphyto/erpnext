import frappe
from frappe import _

from erpnext.stock import get_warehouse_account
from erpnext.stock.doctype.warehouse.warehouse import Warehouse


class WarehouseGP(Warehouse):
    def autoname(self):
        if any(self.get(f) for f in ['row_no', 'lane_no', 'level_no']):
            field_empty = []
            for d in ['row_no', 'lane_no', 'level_no', 'colour', 'store', 'position']:
                if not self.get(d):
                    field = self.meta.get_field(d)
                    field_empty.append(field.label)
            if field_empty:
                temp = ", ".join(field_empty)
                frappe.throw(_("<b>{0}</b> must be set.").format(temp))
            self.name = f"{self.store}-{self.row_no}{self.lane_no}{self.level_no}{self.position}"
            return
        super(WarehouseGP, self).autoname()


def create_warehouse(warehouse_name, properties=None, company=None):
    if not company:
        company = "_Test Company"

    import erpnext

    warehouse_id = erpnext.encode_company_abbr(warehouse_name, company)
    if not frappe.db.exists("Warehouse", warehouse_id):
        w = frappe.new_doc("Warehouse")
        w.warehouse_name = warehouse_name
        w.parent_warehouse = "_Test Warehouse Group - _TC"
        w.company = company
        w.account = get_warehouse_account(warehouse_name, company)
        if properties:
            w.update(properties)
        w.save()
        return w.name
    else:
        return warehouse_id
