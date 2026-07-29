import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, getdate
from frappe.model.naming import parse_naming_series

from erpnext.assets.doctype.asset.asset import Asset


class AssetGP(Asset):
    def autoname(self):
        asset_code = frappe.get_value("Item", self.item_code, "asset_code")
        if asset_code:
            code = frappe.get_value("Asset Code Map", {
                "account": asset_code,
                "parent": 'Accounts Settings',
                "parentfield": "asset_code_map",
            }, "series") or self.naming_series
            self.name = parse_naming_series(code, doc=self)

    def get_asset_movement_data(self):
        reference_doctype = "Purchase Receipt" if self.purchase_receipt else "Purchase Invoice"
        reference_docname = self.purchase_receipt or self.purchase_invoice
        transaction_date = getdate(self.purchase_date)
        assets = [
            {
                "asset": self.name,
                "source_location": self.location,
                "company": self.company,
                "to_employee": self.custodian,
            }
        ]
        return {
            "assets": assets,
            "purpose": "Receipt",
            "company": self.company,
            "transaction_date": transaction_date,
            "reference_doctype": reference_doctype,
            "reference_name": reference_docname,
        }

    def make_asset_movement(self):
        data = self.get_asset_movement_data()
        exist = frappe.db.get_value("Asset Movement Item", {"asset": self.name}, "parent")
        if not exist:
            data['doctype'] = "Asset Movement"
            asset_movement = frappe.get_doc(data).insert()
            asset_movement.submit()

    def update_asset_value_after_depreciation(self):
        super(AssetGP, self).update_asset_value_after_depreciation()
        amount = 0
        for d in self.get("schedules"):
            if d.journal_entry:
                amount += flt(d.depreciation_amount)
        if self.accumulated_depreciation_amount != amount:
            self.db_set("accumulated_depreciation_amount", amount)
