import frappe
from frappe import _
from frappe.utils import flt, today

from erpnext.stock.doctype.pick_list.pick_list import PickList
from erpnext.stock.doctype.batch.batch import get_batch_qty


class PickListGP(PickList):
    def validate(self):
        self.set_missing_values()
        self.validate_for_qty()

    def set_missing_values(self):
        for d in self.locations:
            d.picked_qty = flt(d.picked_qty_view) * flt(d.conversion_factor)
