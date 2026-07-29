import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

import erpnext
from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry


class JournalEntryGP(JournalEntry):
    def validate(self):
        super(JournalEntryGP, self).validate()
        self.validate_cost_center()
        self.validate_gst_input()

    def on_submit(self):
        super(JournalEntryGP, self).on_submit()
        self.link_asset_reference()

    def validate_cost_center(self):
        for d in self.get("accounts"):
            report_type = frappe.db.get_value("Account", d.account, "report_type")
            if report_type != "Profit and Loss":
                continue

            cost_center = erpnext.get_default_cost_center(
                company=self.company, account=d.account
            )
            if cost_center:
                d.cost_center = cost_center
            elif not d.cost_center:
                frappe.throw(
                    _(
                        "Row #{0}: Cost Center is required. No Cost Center found for account {1}. Please add to Account."
                    ).format(frappe.bold(d.idx), frappe.bold(d.account))
                )

    def validate_gst_input(self):
        if self.voucher_type == "GST Input Tax":
            if not self.party_name and not self.invoice_no:
                frappe.throw(
                    _("<b>Party Name/Invoice No</b> should be set for GST Input Tax.")
                )

        elif self.voucher_type == "Journal Entry with GST":
            if self.get("gst_entry") and not self.tax_template_:
                frappe.throw(
                    _("<b>Tax Template</b> Must be set for Journal Entry with GST.")
                )

    def validate_reference_payment(self):
        if not frappe.db.get_single_value(
            "Accounts Settings", "mandatory_reference_on_journal_entry"
        ):
            return

        for d in self.get("accounts"):
            if d.account_type == "Payable":
                if d.is_advance == "No" and d.debit > 0 and not d.reference_name:
                    frappe.throw(
                        _(
                            "<b>Row {}</b>, If not advance payment, Please set reference document against this entry"
                        ).format(d.idx)
                    )
            if d.account_type == "Receivable":
                if d.is_advance == "No" and d.credit > 0 and not d.reference_name:
                    frappe.throw(
                        _(
                            "<b>Row {}</b>, If not advance payment, Please set reference document against this entry"
                        ).format(d.idx)
                    )

    def link_asset_reference(self):
        for d in self.get("accounts"):
            if d.reference_type == "Asset" and d.reference_name and d.credit:
                asset = frappe.get_doc("Asset", d.reference_name)
                for s in asset.get("schedules"):
                    if s.journal_entry:
                        continue
                    start_date = getdate(self.posting_date).replace(day=1)
                    end_date = getdate(self.posting_date)
                    if s.schedule_date >= start_date and s.schedule_date <= end_date:
                        if flt(d.credit, 2) != flt(s.depreciation_amount, 2):
                            frappe.throw(
                                _(
                                    f"Row {d.idx}, Depreciation amount should be <b>{s.depreciation_amount}</b> "
                                )
                            )
                        s.db_set("journal_entry", self.name)
                        idx = cint(s.finance_book_id) or 1
                        finance_books = asset.get("finance_books")[idx - 1]
                        finance_books.value_after_depreciation -= s.depreciation_amount
                        finance_books.db_update()
                        asset.set_status()
                        break

    def set_against_account(self):
        accounts_debited, accounts_credited = [], []
        party_debited, party_credited = [], []
        if self.voucher_type in ("Deferred Revenue", "Deferred Expense"):
            for d in self.get("accounts"):
                if d.reference_type == "Sales Invoice":
                    field = "customer"
                elif d.reference_type == "Purchase Invoice":
                    field = "supplier"
                else:
                    field = "name"

                d.against_account = frappe.db.get_value(
                    d.reference_type, d.reference_name, field
                )
        else:
            accounts = self.get("accounts") + (self.get("gst_entry") or [])
            for d in accounts:
                if flt(d.debit) > 0:
                    accounts_debited.append(d.account or "")
                    party_debited.append(d.get("party") or "")
                if flt(d.credit) > 0:
                    accounts_credited.append(d.account or "")
                    party_credited.append(d.get("party") or "")

            for d in accounts:
                if flt(d.debit) > 0:
                    d.against_account = ", ".join(list(set(accounts_credited)))
                    d.against_party = ", ".join(list(set(party_credited)))
                if flt(d.credit) > 0:
                    d.against_account = ", ".join(list(set(accounts_debited)))
                    d.against_party = ", ".join(list(set(party_debited)))

    def set_total_debit_credit(self):
        self.total_debit, self.total_credit, self.difference = 0, 0, 0
        (
            self.total_debit_in_currency_base,
            self.total_credit_in_currency_base,
            self.difference_in_currency_base,
        ) = (0, 0, 0)
        for d in self.get("accounts") + (self.get("gst_entry") or []):
            if d.debit and d.credit:
                frappe.throw(
                    _("You cannot credit and debit same account at the same time")
                )
            self.total_debit = flt(self.total_debit) + flt(
                d.debit, d.precision("debit")
            )
            self.total_credit = flt(self.total_credit) + flt(
                d.credit, d.precision("credit")
            )
            if d.get("debit_in_currency_base"):
                self.total_debit_in_currency_base = flt(
                    self.total_debit_in_currency_base
                ) + flt(d.debit_in_currency_base, d.precision("debit"))
            if d.get("credit_in_currency_base"):
                self.total_credit_in_currency_base = flt(
                    self.total_credit_in_currency_base
                ) + flt(d.credit_in_currency_base, d.precision("credit"))

        self.difference = flt(
            self.total_debit, self.precision("total_debit")
        ) - flt(self.total_credit, self.precision("total_credit"))

        self.difference_in_currency_base = flt(
            self.total_debit_in_currency_base,
            self.precision("total_debit_in_currency_base"),
        ) - flt(
            self.total_credit_in_currency_base,
            self.precision("total_credit_in_currency_base"),
        )

    def validate_debit_credit_amount(self):
        if not (self.voucher_type == "Exchange Gain Or Loss" and self.multi_currency):
            for d in self.get("accounts"):
                if not flt(d.debit) and not flt(d.credit):
                    frappe.throw(
                        _(
                            "Row {0}: Both Debit and Credit values cannot be zero"
                        ).format(d.idx)
                    )

    def validate_total_debit_and_credit(self):
        self.set_total_debit_credit()
        if not (self.voucher_type == "Exchange Gain Or Loss" and self.multi_currency):
            if self.difference:
                frappe.throw(
                    _("Total Debit must be equal to Total Credit. The difference is {0}").format(
                        self.difference
                    )
                )

    def set_amounts_in_company_currency(self):
        if not self.multi_currency:
            for d in self.get("accounts"):
                d.debit_in_account_currency = flt(
                    d.debit_in_account_currency,
                    d.precision("debit_in_account_currency"),
                )
                d.credit_in_account_currency = flt(
                    d.credit_in_account_currency,
                    d.precision("credit_in_account_currency"),
                )
                d.debit = flt(
                    d.debit_in_account_currency * flt(d.exchange_rate),
                    d.precision("debit"),
                )
                d.credit = flt(
                    d.credit_in_account_currency * flt(d.exchange_rate),
                    d.precision("credit"),
                )

    def validate_multi_currency(self):
        alternate_currency = []
        for d in self.get("accounts"):
            if d.account_currency != self.company_currency:
                d.credit_in_account_currency = d.credit_in_currency_base
                d.debit_in_account_currency = d.debit_in_currency_base
                if d.account_currency not in alternate_currency:
                    alternate_currency.append(d.account_currency)

        if alternate_currency:
            if not self.multi_currency:
                frappe.throw(
                    _(
                        "Please check Multi Currency option to allow accounts with other currency"
                    )
                )
        self.set_exchange_rate()

    def finish_delete(self):
        log = frappe.db.get_value(
            "Deleted Document",
            {"deleted_name": self.name, "deleted_doctype": self.doctype},
        )
        if log:
            frappe.db.set_value("Deleted Document", log, "document_date", self.posting_date)
