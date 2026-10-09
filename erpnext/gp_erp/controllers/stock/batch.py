import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, add_days

from erpnext.stock.doctype.batch.batch import Batch


class BatchGP(Batch):
    def autoname(self):
        super(BatchGP, self).autoname()
        if self.flags.add_last_symbol:
            self.batch_id += "-" + str(self.flags.add_last_symbol)
        self.name = self.batch_id

    def validate(self):
        self.item_has_batch_enabled()
        self.set_batchwise_valuation()
        self.set_status()

    def set_status(self):
        self.status = _get_batch_status(self.batch_qty, self.expiry_date)

    def before_save(self):
        has_expiry_date, shelf_life_in_days = _get_item_shelf_life_in_days(
            self.item, self.get("reference_doctype"), self.get("reference_name")
        )
        if not self.expiry_date and has_expiry_date and shelf_life_in_days:
            self.expiry_date = add_days(self.manufacturing_date, shelf_life_in_days)
        if has_expiry_date and not self.expiry_date:
            frappe.throw(
                msg=_("Please set {0} for Batched Item {1}, which is used to set {2} on Submit.").format(
                    frappe.bold("Expiry Date"),
                    frappe.bold(self.item),
                    frappe.bold("Manufacturing Date"),
                )
            )


def _get_batch_status(batch_qty, expiry_date):
    if flt(batch_qty) <= 0:
        return "Empty"
    if expiry_date and getdate(expiry_date) < getdate():
        return "Expired"
    return "Active"


def _get_item_shelf_life_in_days(item_code, reference_doctype=None, reference_name=None):
    has_expiry_date, shelf_life_in_days = frappe.db.get_value(
        "Item", item_code, ["has_expiry_date", "shelf_life_in_days"]
    ) or (0, None)
    if not (reference_doctype and reference_name):
        return has_expiry_date, shelf_life_in_days
    if not frappe.db.exists("DocType", reference_doctype):
        return has_expiry_date, shelf_life_in_days
    meta = frappe.get_meta(reference_doctype)
    if not meta.has_field("company"):
        return has_expiry_date, shelf_life_in_days
    reference_company = frappe.db.get_value(reference_doctype, reference_name, "company")
    if not reference_company:
        return has_expiry_date, shelf_life_in_days
    mapped_shelf_life = frappe.db.get_value(
        "Shell Life Companies",
        {"parent": item_code, "parenttype": "Item", "company": reference_company},
        "shelf_life_in_days",
    )
    if mapped_shelf_life is not None:
        shelf_life_in_days = mapped_shelf_life
    return has_expiry_date, shelf_life_in_days
