import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


class SalesInvoiceGP(SalesInvoice):
    def validate(self):
        self.validate_item_price_list()
        super(SalesInvoiceGP, self).validate()
        self.set_item_sku()
        self.validate_pledge()
        try:
            self.set_other_reff()
            self.link_internal_company()
        except Exception:
            pass

    def before_insert(self):
        if self.is_return:
            self.naming_series = "CN.###./.YYYY"

    def validate_item_price_list(self):
        from erpnext.stock.get_item_details import get_item_price

        account = frappe.get_cached_value("Company", self.company, "default_discount_account")
        for d in self.get("items"):
            item_price_args = {
                "item_code": d.item_code,
                "price_list": "Standard Selling",
                "customer": self.get("customer"),
                "uom": d.get("uom"),
                "transaction_date": self.get("posting_date"),
                "batch_no": d.get("batch_no"),
            }
            d.discount_account = account
            temp = get_item_price(item_price_args, d.item_code)
            if temp:
                temp = temp[0]

            if temp:
                d.price_list_rate = temp[1]

    def validate_item_cost_centers(self):
        for item in self.items:
            if item.cost_center:
                cost_center_company = frappe.get_cached_value(
                    "Cost Center", item.cost_center, "company"
                )
                if cost_center_company != self.company:
                    frappe.throw(
                        _("Row #{0}: Cost Center {1} does not belong to company {2}").format(
                            frappe.bold(item.idx),
                            frappe.bold(item.cost_center),
                            frappe.bold(self.company),
                        )
                    )
            else:
                cost_center = erpnext.get_default_cost_center(
                    company=self.company, account=item.income_account
                )
                if cost_center:
                    item.cost_center = cost_center
                else:
                    frappe.throw(
                        _(
                            "Row #{0}: Cost Center is required. No mapping found for account {1} in Cost Center Settings."
                        ).format(frappe.bold(item.idx), frappe.bold(item.income_account))
                    )

    def set_item_sku(self):
        doc = frappe.get_doc("Customer", self.customer)
        for d in self.get("items"):
            d.customer_sku = doc.get_item_sku(d.item_code)
            d.customer_sku_name = doc.get_item_sku(d.item_code, "sku_name")

    def validate_pledge(self):
        if self.customer == "Donor":
            self.is_pledge = 1
            if not self.contact_display:
                self.contact_display = self.donor_name

    def set_other_reff(self):
        for d in self.get("items"):
            if not d.sales_order:
                if d.get("dn_detail"):
                    dn_name, so_detail, so_name = (
                        frappe.get_value(
                            "Delivery Note Item",
                            {"name": d.dn_detail, "docstatus": 1},
                            ["parent", "so_detail", "against_sales_order"],
                        )
                        or (None, None, None)
                    )
                    if so_detail:
                        d.so_detail = so_detail
                        d.sales_order = so_name

            if not d.delivery_note:
                if d.get("so_detail"):
                    dn_detail, dn_name = frappe.get_value(
                        "Delivery Note Item",
                        {"so_detail": d.so_detail, "docstatus": 1},
                        ["name", "parent"],
                    ) or (None, None)

                    if dn_detail:
                        frappe.db.set_value(
                            "Delivery Note Item", dn_detail, "si_detail", d.name
                        )
                        frappe.db.set_value(
                            "Delivery Note Item",
                            dn_detail,
                            "against_sales_invoice",
                            d.parent,
                        )
                        d.dn_detail = dn_detail
                        d.delivery_note = dn_name

            dn_name = d.delivery_note

        if not self.delivery_note:
            self.delivery_note = dn_name

    def link_internal_company(self):
        so_number = next(
            (d.sales_order for d in self.items if d.sales_order), None
        )
        if not so_number:
            return

        inter_po_name = frappe.get_value(
            "Sales Order", so_number, "inter_company_order_reference"
        )
        if not inter_po_name:
            return

        represents_company = frappe.get_value(
            "Sales Order", so_number, "represents_company"
        )
        inter_pi_number = frappe.db.sql(
            """
                SELECT DISTINCT pii.parent
                FROM `tabPurchase Invoice Item` pii
                JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
                WHERE
                    pii.purchase_order = %s
                    AND pi.docstatus = 1
                ORDER BY pi.creation DESC
                LIMIT 1
            """,
            inter_po_name,
            as_dict=False,
        )

        if not inter_pi_number:
            return

        inter_pi_number = inter_pi_number[0][0] if inter_pi_number else None
        self.inter_company_invoice_reference = inter_pi_number
        self.represents_company = represents_company

    def get_gl_entries(self, warehouse_account=None):
        gl_entries = super(SalesInvoiceGP, self).get_gl_entries(warehouse_account)
        return self._remap_gl_against(gl_entries)

    def _remap_gl_against(self, gl_entries):
        for gle in gl_entries:
            if gle.get("against") == self.customer:
                gle["against"] = self.debit_to
                gle["against_party"] = self.customer
        return gl_entries

    def finish_delete(self):
        log = frappe.db.get_value(
            "Deleted Document",
            {"deleted_name": self.name, "deleted_doctype": self.doctype},
        )
        if log:
            frappe.db.set_value("Deleted Document", log, "document_date", self.posting_date)
