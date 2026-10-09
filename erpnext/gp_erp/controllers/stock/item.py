import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, strip_html
import re

from erpnext.stock.doctype.item.item import Item
from erpnext.stock.get_item_details import get_uom_conv_factor


class ItemGP(Item):
    def validate(self):
        if not strip_html(cstr(self.description)).strip():
            self.description = self.item_name
        self.force_to_non_stock()
        self.validate_uom()
        self.validate_description()
        self.add_default_uom_in_conversion_factor_table()
        self.set_opening_stock()
        self.set_item_default()
        self.validate_item_type()
        self.validate_naming_series()
        self.validate_fixed_asset()
        self.clear_retain_sample()
        self.validate_retain_sample()
        self.validate_package()
        self.validate_uom_conversion_factor()
        self.validate_customer_provided_part()
        self.update_defaults_from_item_group()
        self.validate_end_of_life()
        self.validate_auto_reorder_enabled_in_stock_settings()
        self.cant_change()
        self.validate_item_tax_net_rate_range()
        self.insert_department()
        self.set_material_number()
        self.validate_debit_note_item()
        self.set_asset_category()
        self.update_uom_global_description()
        self.change_description()
        set_item_tax_from_hsn_code(self)
        if not self.is_new():
            self.old_item_group = frappe.db.get_value(self.doctype, self.name, "item_group")

    def on_trash(self):
        self.validate_foms_item()

    def change_description(self):
        prev_doc = self.get_doc_before_save()
        cur_description = strip_html(cstr(self.description)).strip()
        if prev_doc and prev_doc.item_name == cur_description:
            self.description = self.item_name

    def validate_foms_item(self):
        if self.flags.allow_delete:
            return
        if self.get("foms_raw_id") or self.get("foms_product_id"):
            frappe.throw(_("Cannot delete FOMS's Item, you can only disable it"))

    def force_to_non_stock(self):
        if frappe.db.get_single_value("Stock Settings", "force_to_non_stock_item"):
            self.is_stock_item = 0

    def validate_debit_note_item(self):
        if self.get("debit_note_item"):
            if frappe.db.exists("Item", {"debit_note_item": 1, "name": ['!=', self.name]}):
                frappe.throw(_("Cannot make more item debit note"))

    def insert_department(self):
        if not self.get("item_department"):
            root_dept = frappe.get_value("Department", {"lft": 1})
            if root_dept:
                row = self.append("item_department")
                row.department = root_dept

    def update_uom_global_description(self):
        old_doc = self.get_doc_before_save()
        for d in self.uoms:
            current_master_desc = frappe.db.get_value("UOM", d.uom, "global_description")
            if not old_doc:
                d.origin_description = current_master_desc
                d.global_description = current_master_desc
                continue
            old_row = next((row for row in old_doc.uoms if row.uom == d.uom), None)
            if not old_row:
                d.origin_description = current_master_desc
                d.global_description = current_master_desc
                continue
            if d.global_description != old_row.global_description:
                frappe.db.set_value("UOM", d.uom, "global_description", d.global_description)
                d.origin_description = d.global_description
            else:
                if d.global_description != current_master_desc:
                    d.global_description = current_master_desc
                    d.origin_description = current_master_desc

    def validate_package(self):
        if len(self.get("packaging") or []):
            self.is_package_item = 1
        else:
            self.is_package_item = 0
        self.sync_uom_from_package()

    def sync_uom_from_package(self):
        if not self.get("packaging"):
            return
        default = None
        for d in self.get("packaging"):
            row = self.get("uoms", {"uom": d.packaging})
            if row:
                row = row[0]
                row.conversion_factor = flt(d.weight)
                row.cf_view = flt(d.weight)
            else:
                row = self.append("uoms")
                row.uom = d.packaging
                row.to_uom = self.stock_uom
                row.conversion_factor = flt(d.weight)
                row.is_packaging = 1
                row.cf_view = flt(d.weight)
            if d.default:
                if not default:
                    default = d.packaging
                else:
                    frappe.throw("Row {}, Cannot have more than 1 default row packaging".format(d.idx))
        if not default and self.get("packaging"):
            self.packaging[0].default = 1
            default = self.packaging[0].packaging
        self.default_packaging = default
        for d in list(self.get("uoms", {"is_packaging": 1})):
            row = self.get("packaging", {"packaging": d.uom})
            if not row:
                self.remove(d)

    def validate_fixed_asset(self):
        if self.is_fixed_asset:
            if self.is_stock_item:
                frappe.throw(_("Fixed Asset Item must be a non-stock item"))
            if not self.is_new() and self.stock_ledger_created():
                frappe.throw(_("Cannot be a fixed asset item as Stock Ledger is created."))
            if not self.asset_code:
                frappe.throw(_("Asset Code is mandatory for Fixed Asset item"))
        if not self.is_fixed_asset:
            asset = frappe.db.get_all("Asset", filters={"item_code": self.name, "docstatus": 1}, limit=1)
            if asset:
                frappe.throw(_('"Is Fixed Asset" cannot be unchecked, as Asset record exists against the item'))

    def set_asset_category(self):
        if not self.asset_code:
            return
        from erpnext.assets.doctype.asset.asset import get_default_asset_code_data
        data = get_default_asset_code_data(self.asset_code) or {}
        if not self.asset_category:
            self.asset_category = data.get("asset_category")
        company = data.get("company") or erpnext.get_default_company()
        do_set = False
        for d in self.get("item_defaults"):
            if d.company == company:
                do_set = True
                d.expense_account = data.get("account")
        if not do_set:
            self.append("item_defaults", {"company": company, "expense_account": data.get("account")})

    def validate_uom_conversion_factor(self):
        if not self.uoms:
            return
        resolved = {self.stock_uom: 1.0}
        for d in self.uoms:
            if d.idx == 1:
                d.description = "Stock UOM Value"
                d.conversion_factor = 1
                d.cf_view = 1
                resolved[d.uom] = 1.0
                continue
            if d.to_uom:
                continue
            value = get_uom_conv_factor(d.uom, self.stock_uom)
            if value:
                d.conversion_factor = value
                resolved[d.uom] = flt(value)
                d.description = f"1 {d.uom} equal to {d.cf_view} {self.stock_uom}"
                continue
            d.description = f"1 {d.uom} equal to {d.cf_view} {self.stock_uom}"
            d.conversion_factor = flt(d.cf_view)
            resolved[d.uom] = flt(d.conversion_factor)
        for _pass in range(len(self.uoms) + 1):
            any_resolved = False
            for d in self.uoms:
                if d.idx == 1 or not d.to_uom or d.uom in resolved:
                    continue
                if d.to_uom not in resolved:
                    continue
                to_cf = resolved[d.to_uom]
                cf = flt(d.cf_view) * to_cf
                d.description = f"1 {d.uom} equal to {d.cf_view} {d.to_uom} (= {flt(cf, 7)} {self.stock_uom})"
                d.conversion_factor = flt(cf)
                resolved[d.uom] = flt(cf)
                any_resolved = True
            if not any_resolved:
                break
        for d in self.uoms:
            if d.idx == 1 or not d.to_uom:
                continue
            if d.uom not in resolved:
                frappe.throw(
                    _("Row {0}: UOM '{1}' -> '{2}' cannot be traced back to Stock UOM '{3}'. "
                      "Ensure all UOMs in the chain are defined in the conversion table.").format(
                        d.idx, d.uom, d.to_uom, self.stock_uom
                    )
                )

    def set_material_number(self):
        if self.disabled:
            return
        from frappe.model.naming import parse_naming_series
        if self.get("material_group"):
            series = parse_material_group_series(self.material_group)
            if not self.get("material_number") and not self.disabled:
                self.material_number = parse_naming_series(series)
        else:
            self.material_number = ""


def parse_material_group_series(material_group):
    name = frappe.db.exists('Material Group', material_group)
    if not name:
        frappe.throw(_("Cannot find Material Group {0}").format(material_group))
    temp = frappe.get_value("Material Group", material_group, ['number_start', 'number_end'], as_dict=1)
    diff = cint(temp.number_end) - cint(temp.number_start)
    replacer = "."
    for d in cstr(diff):
        replacer += "#"
    series = re.sub(f'{diff}$', replacer, cstr(temp.number_end))
    return series
