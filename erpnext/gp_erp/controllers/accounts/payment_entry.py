import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry


class PaymentEntryGP(PaymentEntry):
    def validate_allocated_amount(self):
        super(PaymentEntryGP, self).validate_allocated_amount()

        if flt(self.unallocated_amount) > 0.01:
            if self.payment_type == "Pay":
                frappe.throw(
                    _(
                        "The amount paid is not equal to the total allocated amount. Please check the allocated amount on each invoice is correct."
                    )
                )
            else:
                frappe.throw(
                    _(
                        "The amount received is not equal to the total allocated amount. Please check the allocated amount on each invoice is correct."
                    )
                )

    def add_bank_gl_entries(self, gl_entries):
        acc_type = frappe.get_value("Account", self.paid_from, "account_type")

        if self.payment_type in ("Pay", "Internal Transfer"):
            data = {
                "account": self.paid_from,
                "account_currency": self.paid_from_account_currency,
                "against": self.party if self.payment_type == "Pay" else self.paid_to,
                "credit_in_account_currency": self.paid_amount,
                "credit": self.base_paid_amount,
                "cost_center": self.cost_center,
                "post_net_value": True,
            }
            if acc_type == "Payable":
                data["party_type"] = self.party_type
                data["party"] = self.party

            gl_entries.append(self.get_gl_dict(data, item=self))

        if self.payment_type in ("Receive", "Internal Transfer"):
            data = {
                "account": self.paid_to,
                "account_currency": self.paid_to_account_currency,
                "against": self.party if self.payment_type == "Receive" else self.paid_from,
                "debit_in_account_currency": self.received_amount,
                "debit": self.base_received_amount,
                "cost_center": self.cost_center,
            }
            if acc_type == "Receivable":
                data["party_type"] = self.party_type
                data["party"] = self.party

            gl_entries.append(self.get_gl_dict(data, item=self))

    def finish_delete(self):
        log = frappe.db.get_value(
            "Deleted Document",
            {"deleted_name": self.name, "deleted_doctype": self.doctype},
        )
        if log:
            frappe.db.set_value("Deleted Document", log, "document_date", self.posting_date)
