import frappe
import erpnext
from frappe import _
from frappe.utils import cstr
from frappe.model.naming import parse_naming_series

from erpnext.buying.doctype.supplier.supplier import Supplier


class SupplierGP(Supplier):
    def set_code(self, force=False):
        comp_abbr = cstr(frappe.get_value("Company", self.company, "series_abbr"))
        series = self.supplier_code_series or "S0.####"
        if comp_abbr and comp_abbr not in series:
            series = comp_abbr + series
            self.supplier_code_series = series
        if not self.supplier_code:
            self.supplier_code = parse_naming_series(series, doc=self)
        if self.supplier_code and not force:
            if comp_abbr and comp_abbr not in self.supplier_code:
                self.supplier_code = comp_abbr + self.supplier_code
            else:
                return
        exists = frappe.db.get_value("Supplier", {"name": ["!=", self.name], "supplier_code": self.supplier_code})
        if exists:
            frappe.throw("Supplier code <b>{}</b> already used.".format(self.supplier_code))
        self.set_account_default()

    def set_account_default(self):
        doc = frappe.get_doc("Buying Settings")
        company = erpnext.get_default_company()
        for d in doc.get("default_supplier_account"):
            series = d.code.replace("...", "")
            if series in self.supplier_code:
                row = self.get("accounts", {"company": company})
                if not row:
                    row = self.append("accounts")
                    row.account = d.account
                    row.company = company

    def after_insert(self):
        self.validate_item_supplier(after_insert=1)

    def update_series(self):
        next_series = _get_exists_series(self.supplier_code_series)
        if next_series == self.supplier_code:
            parse_naming_series(self.supplier_code_series, doc=self)

    def validate_item_supplier(self, after_insert=False):
        def _process(value, typ="Add"):
            data = {
                "party_type": "Supplier",
                "party": self.name,
                "restrict_based_on": "Item",
                "based_on_value": value
            }
            exist = frappe.db.exists("Party Specific Item", data)
            if typ == "Add":
                if exist:
                    return exist
                else:
                    doc = frappe.new_doc("Party Specific Item")
                    doc.update(data)
                    doc.insert(ignore_permissions=1)
                    return doc.name
            else:
                if not exist:
                    return
                frappe.delete_doc("Party Specific Item", exist)

        old_doc = self.get_doc_before_save()
        if not old_doc:
            if after_insert and self.enable_item_supplier:
                for d in self.get("item_supplier"):
                    _process(d.item_code, "Add")
            return
        old_list = [x.item_code for x in old_doc.get("item_supplier")]
        cur_list = []
        for d in self.get("item_supplier"):
            cur_list.append(d.item_code)
            if not self.enable_item_supplier:
                _process(d.item_code, "Delete")
            else:
                _process(d.item_code, "Add")
        if self.enable_item_supplier:
            for d in old_doc.get("item_supplier"):
                if d.item_code not in cur_list:
                    _process(d.item_code, "Delete")


def _get_exists_series(series):
    naming = frappe.model.naming.NamingSeries(series)

    def _fake_counter(_prefix, digits):
        count = naming.get_current_value() + 1
        return str(count).zfill(digits)

    return parse_naming_series(series, number_generator=_fake_counter)
