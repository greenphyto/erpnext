import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.manufacturing.doctype.job_card.job_card import JobCard

COMPLETE_OPERATION = "Harvesting"


class JobCardGP(JobCard):
    def on_submit(self):
        self.update_work_order()
        self.set_transferred_qty()

    def validate_transfer_qty(self):
        if self.items and flt(self.transferred_qty, 2) < flt(self.for_quantity - 0.01, 2):
            frappe.throw(
                _(
                    "Materials needs to be transferred to the work in progress warehouse for the job card {0}"
                ).format(self.name)
            )

    def set_status(self, update_status=False):
        if self.status == "On Hold" and self.docstatus == 0:
            return
        single_complete = frappe.db.get_single_value(
            "Manufacturing Settings", "allow_single_completed_work_order"
        )
        self.status = {0: "Open", 1: "Submitted", 2: "Cancelled"}[self.docstatus or 0]
        if self.work_order:
            wo_doc = frappe.get_all("Work Order", filters={"name": self.work_order}, fields=["skip_transfer"], limit=1)
            if wo_doc and not wo_doc[0].skip_transfer:
                if not self.total_completed_qty and not self.time_logs:
                    self.status = "Open"
                if self.time_logs:
                    self.status = "Work In Progress"
                if self.docstatus == 1:
                    if single_complete:
                        self.status = "Completed"
                    elif (self.for_quantity <= self.total_completed_qty or not self.items):
                        self.status = "Completed"
        if update_status:
            self.db_set("status", self.status)
