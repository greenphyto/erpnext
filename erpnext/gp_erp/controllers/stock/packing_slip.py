import math

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.stock.doctype.packing_slip.packing_slip import PackingSlip


class PackingSlipGP(PackingSlip):
    def calculate_net_total_pkg(self):
        if not flt(self.unit_per_carton):
            self.unit_per_carton = 12
        if not flt(self.carton_weight):
            self.carton_weight = 0.435

        self.net_weight_uom = self.items[0].weight_uom if self.items else None
        self.gross_weight_uom = self.net_weight_uom

        net_weight_pkg = 0
        total_qty = 0
        for item in self.items:
            if item.weight_uom != self.net_weight_uom:
                frappe.throw(
                    _(
                        "Different UOM for items will lead to incorrect (Total) Net Weight value. Make sure that Net Weight of each item is in the same UOM."
                    )
                )

            item.cartons = math.ceil(flt(item.qty) / flt(self.unit_per_carton))
            item.net_weight = flt(item.unit_weight) * flt(item.qty)
            item.gross_weight = item.net_weight + (item.cartons * flt(self.carton_weight))

            weight_grams = flt(item.unit_weight) * 1000
            item.uom_view = "{0} Gr".format(cint(weight_grams))

            net_weight_pkg += item.net_weight
            total_qty += flt(item.qty)

        self.net_weight_pkg = round(net_weight_pkg, 2)
        self.total_qty = total_qty

        if not flt(self.gross_weight_pkg):
            self.gross_weight_pkg = self.net_weight_pkg
