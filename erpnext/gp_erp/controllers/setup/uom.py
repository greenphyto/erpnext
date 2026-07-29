import frappe
from frappe import _

from erpnext.setup.doctype.uom.uom import UOM


class UOMGP(UOM):
    def validate(self):
        if not self.global_description:
            self.global_description = self.uom_name
