import frappe
from frappe import _

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
