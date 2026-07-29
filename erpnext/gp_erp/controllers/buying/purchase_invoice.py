import frappe
from frappe import _, get_link_to_form
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, getdate, add_days

from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice


class PurchaseInvoiceGP(PurchaseInvoice):
    def validate(self):
        super(PurchaseInvoiceGP, self).validate()
        self.validate_gst_input()
        try:
            self.link_internal_company()
        except Exception:
            pass

    def validate_gst_input(self):
        if self.get("gst_input_tax") and not self.get("base_value_for_gst_input"):
            frappe.throw(_("Please set Base Value for GST input"))
        self.base_currency_of_base_value = flt(self.base_value_for_gst_input) * self.conversion_rate

    def link_internal_company(self):
        if not self.is_internal_supplier:
            return

        po_number = next(
            (d.purchase_order for d in self.items if d.purchase_order), None
        )
        if not po_number:
            return

        inter_so_name = frappe.get_value(
            "Purchase Order", po_number, "inter_company_order_reference"
        )
        if not inter_so_name:
            inter_so_name = frappe.db.get_value(
                "Sales Order",
                {"inter_company_order_reference": po_number, "docstatus": 1},
            )
            if not inter_so_name:
                return
            frappe.db.set_value(
                "Purchase Order",
                po_number,
                "inter_company_order_reference",
                inter_so_name,
            )

        represents_company = frappe.get_value(
            "Purchase Order", po_number, "represents_company"
        )
        inter_si_number = frappe.db.sql(
            """
                SELECT DISTINCT sii.parent
                FROM `tabSales Invoice Item` sii
                JOIN `tabSales Invoice` si ON si.name = sii.parent
                WHERE
                    sii.sales_order = %s
                    AND si.docstatus = 1
                ORDER BY si.creation DESC
                LIMIT 1
            """,
            inter_so_name,
            as_dict=False,
        )

        if not inter_si_number:
            return

        inter_si_number = inter_si_number[0][0] if inter_si_number else None
        if inter_si_number:
            frappe.db.set_value(
                "Sales Invoice",
                inter_si_number,
                "inter_company_invoice_reference",
                self.name,
            )

        self.inter_company_invoice_reference = inter_si_number
        self.represents_company = represents_company

    def get_gl_entries(self, warehouse_account=None):
        gl_entries = super(PurchaseInvoiceGP, self).get_gl_entries(warehouse_account)
        return self._remap_gl_against(gl_entries)

    def _remap_gl_against(self, gl_entries):
        for gle in gl_entries:
            if gle.get("against") == self.supplier:
                gle["against"] = self.credit_to
                gle["against_party"] = self.supplier
        return gl_entries

    def finish_delete(self):
        log = frappe.db.get_value(
            "Deleted Document",
            {"deleted_name": self.name, "deleted_doctype": self.doctype},
        )
        if log:
            frappe.db.set_value("Deleted Document", log, "document_date", self.posting_date)


@frappe.whitelist()
@frappe.read_only()
def hide_older_cancelled_document():
    from frappe.desk.reportview import get, get_form_params

    args = get_form_params()
    data = get()
    new_values = []
    skip_filter = False
    for d in args.get("filters"):
        if "Cancelled" in d:
            skip_filter = 1
        if "docstatus" in d and "2" in d:
            skip_filter = 1

    if data and not skip_filter:
        docstatus_index = 0
        modified_index = 0
        for i, d in enumerate(data["keys"]):
            if "docstatus" == d:
                docstatus_index = i
            if "modified" == d:
                modified_index = i
        for d in data["values"]:
            if d[docstatus_index] == 2 and getdate(d[modified_index]) < add_days(getdate(), -1):
                continue
            else:
                new_values.append(d)
        data["values"] = new_values

    return data


@frappe.whitelist()
@frappe.read_only()
def make_payment_approval(source_name, target_doc=None):
    def postprocess(source_doc, target_doc):
        row = target_doc.append("invoices")
        row.selected = 1
        row.invoice_no = source_doc.name
        row.party = source_doc.supplier
        row.amount = flt(source_doc.outstanding_amount)
        row.basic_amount = flt(source_doc.outstanding_amount)
        row.currency = source_doc.currency
        row.exchange_rate = flt(source_doc.conversion_rate)

        supplier = frappe.get_doc("Supplier", source_doc.supplier)
        if supplier.default_bank_account_no:
            row.supplier_bank_no = supplier.default_bank_account_no
            bank_account = frappe.get_doc("Bank Number", supplier.default_bank_account_no)
            if bank_account.bank:
                row.supplier_bank = bank_account.bank
                bank = frappe.get_doc("Bank", bank_account.bank)
                row.swift = bank.swift_number

    doc = get_mapped_doc(
        "Purchase Invoice",
        source_name,
        {
            "Purchase Invoice": {
                "doctype": "Payment Approval",
                "validation": {"docstatus": ["=", 1]},
            }
        },
        target_doc,
        postprocess,
    )
    return doc


@frappe.whitelist()
def update_bank_number_details(
    bank_number_name: str,
    bank_number: str = None,
    bank_account_name: str = None,
    bank: str = None,
    branch: str = None,
    swift: str = None,
):
    bn = frappe.get_doc("Bank Number", bank_number_name)
    if not bn.has_permission("write"):
        frappe.throw(_("No write permission for Bank Number"))

    if bank_number is not None:
        bn.bank_number = bank_number
    if bank_account_name is not None:
        bn.bank_account_name = bank_account_name
    if bank is not None:
        bn.bank = bank
    if branch is not None:
        bn.branch = branch
    if swift is not None:
        bn.swift = swift

    bn.save()

    return {
        "name": bn.name,
        "bank_number": bn.get("bank_number"),
        "bank_account_name": bn.get("bank_account_name"),
        "bank": bn.get("bank"),
        "branch": bn.get("branch"),
        "swift": bn.get("swift"),
        "currency": bn.get("currency"),
    }
