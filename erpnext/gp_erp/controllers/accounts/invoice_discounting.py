import frappe
from frappe import _
from frappe.utils import flt

import erpnext
from erpnext.accounts.doctype.invoice_discounting.invoice_discounting import InvoiceDiscounting


class InvoiceDiscountingGP(InvoiceDiscounting):
    def get_gl_entries(self):
        gl_entries = []

        # discharge loan
        gl_entries.append(
            self.get_gl_dict(
                {
                    "account": self.bank_account,
                    "debit_in_account_currency": flt(self.total_amount) - flt(self.bank_charges),
                    "cost_center": erpnext.get_default_cost_center(self.company, self.bank_account),
                },
            )
        )

        if self.bank_charges:
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": self.bank_charges_account,
                        "debit_in_account_currency": flt(self.bank_charges),
                        "cost_center": erpnext.get_default_cost_center(self.company, self.bank_charges_account),
                    },
                )
            )

        gl_entries.append(
            self.get_gl_dict(
                {
                    "account": self.short_term_loan,
                    "credit_in_account_currency": flt(self.total_amount),
                    "cost_center": erpnext.get_default_cost_center(self.company, self.short_term_loan),
                    "reference_type": "Invoice Discounting",
                    "reference_name": self.name,
                },
            )
        )

        for d in self.get("invoices"):
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": self.accounts_receivable_discounted,
                        "debit_in_account_currency": flt(d.outstanding_amount),
                        "cost_center": erpnext.get_default_cost_center(self.company, self.accounts_receivable_discounted),
                        "reference_type": "Invoice Discounting",
                        "reference_name": self.name,
                        "party_type": "Customer",
                        "party": d.customer,
                    },
                )
            )
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": self.accounts_receivable_credit,
                        "credit_in_account_currency": flt(d.outstanding_amount),
                        "cost_center": erpnext.get_default_cost_center(self.company, self.accounts_receivable_credit),
                        "reference_type": "Invoice Discounting",
                        "reference_name": self.name,
                        "party_type": "Customer",
                        "party": d.customer,
                    },
                )
            )

        return gl_entries

    def get_unsecured_gl_entries(self):
        gl_entries = []

        gl_entries.append(
            self.get_gl_dict(
                {
                    "account": self.short_term_loan,
                    "debit_in_account_currency": flt(self.total_amount),
                    "cost_center": erpnext.get_default_cost_center(self.company, self.short_term_loan),
                    "reference_type": "Invoice Discounting",
                    "reference_name": self.name,
                },
            )
        )
        gl_entries.append(
            self.get_gl_dict(
                {
                    "account": self.bank_account,
                    "credit_in_account_currency": flt(self.total_amount),
                    "cost_center": erpnext.get_default_cost_center(self.company, self.bank_account),
                },
            )
        )

        for d in self.get("invoices"):
            outstanding_amount = flt(d.outstanding_amount)
            if outstanding_amount:
                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": self.accounts_receivable_discounted,
                            "credit_in_account_currency": flt(outstanding_amount),
                            "cost_center": erpnext.get_default_cost_center(self.company, self.accounts_receivable_discounted),
                            "reference_type": "Invoice Discounting",
                            "reference_name": self.name,
                            "party_type": "Customer",
                            "party": d.customer,
                        },
                    )
                )
                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": self.accounts_receivable_unpaid,
                            "debit_in_account_currency": flt(outstanding_amount),
                            "cost_center": erpnext.get_default_cost_center(self.company, self.accounts_receivable_unpaid),
                            "reference_type": "Invoice Discounting",
                            "reference_name": self.name,
                            "party_type": "Customer",
                            "party": d.customer,
                        },
                    )
                )

        return gl_entries
